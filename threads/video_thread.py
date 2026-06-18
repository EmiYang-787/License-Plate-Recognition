"""
视频文件处理线程
职责：读取视频帧 → 压缩后发送到UI显示 → 异步提交原帧给AI处理线程 → 轮询识别结果
AI识别在独立线程中执行，不阻塞视频播放。
"""
import time
import cv2
from PyQt5.QtCore import QThread, pyqtSignal

from threads.processing_thread import ProcessingThread

# 显示帧的最大尺寸（大幅减少 Qt 跨线程信号的数据拷贝量）
DISPLAY_MAX_WIDTH = 720
DISPLAY_MAX_HEIGHT = 480


class VideoThread(QThread):
    # 信号定义（全部从 VideoThread 自己的线程发射，保证 Qt 信号投递正确）
    frame_signal = pyqtSignal(object)       # 压缩后的帧（numpy.ndarray）→ UI显示
    result_signal = pyqtSignal(list)        # 识别结果列表 → UI展示
    stopped_signal = pyqtSignal()           # 线程停止信号

    def __init__(self, video_path, process_frame_func, handle_plate_func,
                 parent=None, skip_frames=2):
        super().__init__(parent)
        self.video_path = video_path
        self.process_frame = process_frame_func
        self.handle_plate = handle_plate_func
        self.skip_frames = skip_frames
        self._is_running = False
        self._proc_thread = None

    @staticmethod
    def _resize_for_display(frame, max_w=DISPLAY_MAX_WIDTH, max_h=DISPLAY_MAX_HEIGHT):
        """将帧缩放到显示尺寸，大幅减少信号数据量（6MB → ~1MB）"""
        h, w = frame.shape[:2]
        if w <= max_w and h <= max_h:
            return frame
        scale = min(max_w / w, max_h / h)
        new_w, new_h = int(w * scale), int(h * scale)
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_NEAREST)

    def run(self):
        self._is_running = True

        # 启动独立的AI处理线程
        self._proc_thread = ProcessingThread(
            process_frame_func=self.process_frame,
            handle_plate_func=self.handle_plate,
            skip_frames=self.skip_frames
        )
        self._proc_thread.start()

        cap = cv2.VideoCapture(self.video_path)

        if not cap.isOpened():
            print(f"[VideoThread] 无法打开视频: {self.video_path}")
            self._cleanup()
            self.stopped_signal.emit()
            return

        # 显示帧率控制：约 15fps（监控视频足够流畅，且不给主线程压力）
        _display_interval = 1.0 / 15.0
        _last_display_time = 0.0

        while self._is_running:
            ret, frame = cap.read()
            if not ret:
                break

            now = time.perf_counter()

            # 1. 节流发送压缩后的帧到UI显示
            if now - _last_display_time >= _display_interval:
                display_frame = self._resize_for_display(frame)
                self.frame_signal.emit(display_frame)
                _last_display_time = now

            # 2. 异步提交帧拷贝给AI处理线程（非阻塞）
            #    copy() 是必须的：cv2.VideoCapture 可能复用内部缓冲区，
            #    不拷贝会导致处理线程中的帧数据被下一帧覆盖
            if self._proc_thread and self._proc_thread.isRunning():
                self._proc_thread.submit_frame(frame.copy())

            # 3. 轮询AI处理结果，从VideoThread自己的线程发射Qt信号
            for results in self._proc_thread.get_results():
                self.result_signal.emit(results)

            # 控制读取帧率约30fps
            self.msleep(33)

        cap.release()
        self._cleanup()
        self.stopped_signal.emit()

    def _cleanup(self):
        """停止AI处理线程"""
        if self._proc_thread:
            self._proc_thread.stop()

    def stop(self):
        """安全停止线程"""
        self._is_running = False
        self._cleanup()
        self.wait(1500)
