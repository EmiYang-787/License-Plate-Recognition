"""
视频文件处理线程
职责：读取视频帧 → 发送帧到UI显示 → 调用AI接口识别 → 发送结果
"""
from PyQt5.QtCore import QThread, pyqtSignal
import cv2


class VideoThread(QThread):
    # 信号定义
    frame_signal = pyqtSignal(object)       # 原始帧（numpy.ndarray）→ 用于UI显示
    result_signal = pyqtSignal(list)        # 识别结果列表 → 用于UI展示
    stopped_signal = pyqtSignal()           # 线程停止信号

    def __init__(self, video_path, process_frame_func, handle_plate_func,
                 parent=None, skip_frames=2):
        """
        :param video_path: 视频文件路径
        :param process_frame_func: AI接口 process_frame(frame) → List[str]
        :param handle_plate_func: 业务接口 handle_plate(plate) → dict
        :param skip_frames: 跳帧数（每N帧识别一次，降低CPU占用）
        """
        super().__init__(parent)
        self.video_path = video_path
        self.process_frame = process_frame_func      # 成员A提供的接口
        self.handle_plate = handle_plate_func        # 成员B提供的接口
        self.skip_frames = skip_frames
        self._is_running = False
        self._frame_count = 0

    def run(self):
        self._is_running = True
        cap = cv2.VideoCapture(self.video_path)

        if not cap.isOpened():
            print(f"[VideoThread] 无法打开视频: {self.video_path}")
            self.stopped_signal.emit()
            return

        while self._is_running:
            ret, frame = cap.read()
            if not ret:
                break

            self._frame_count += 1

            # 1. 每帧都发送给UI显示（保证画面流畅）
            self.frame_signal.emit(frame)

            # 2. 按跳帧策略进行识别（在子线程执行，不卡UI）
            if self._frame_count % (self.skip_frames + 1) == 0:
                try:
                    plates = self.process_frame(frame)  # AI识别
                    results = []
                    for plate in plates:
                        result = self.handle_plate(plate)  # 业务处理
                        results.append(result)
                    if results:
                        self.result_signal.emit(results)
                except Exception as e:
                    print(f"[VideoThread] 识别异常: {e}")

            # 控制帧率约30fps
            self.msleep(33)

        cap.release()
        self.stopped_signal.emit()

    def stop(self):
        """安全停止线程"""
        self._is_running = False
        self.wait(1500)