"""
AI 识别处理线程
职责：从帧队列中获取最新帧 → 调用AI接口识别 → 调用业务接口 → 放入结果队列
与视频/摄像头线程完全解耦，不阻塞画面播放。

结果通过 Python queue.Queue 传回（而非 Qt 信号），
因为 VideoThread 覆盖了 run() 没有 Qt 事件循环，跨线程 Qt 信号无法投递。
"""
import queue
from PyQt5.QtCore import QThread


class ProcessingThread(QThread):
    """独立的 AI 处理线程，异步消费帧队列"""

    def __init__(self, process_frame_func, handle_plate_func,
                 skip_frames=2, parent=None):
        """
        :param process_frame_func: AI接口 process_frame(frame) → List[str]
        :param handle_plate_func: 业务接口 handle_plate(plate) → dict
        :param skip_frames: 跳帧数（每N+1帧识别一次）
        """
        super().__init__(parent)
        self.process_frame = process_frame_func
        self.handle_plate = handle_plate_func
        self.skip_frames = skip_frames
        self._is_running = False
        self._frame_count = 0

        # 输入队列：maxsize=1，只保留最新一帧
        self._frame_queue = queue.Queue(maxsize=1)

        # 输出队列：识别结果，由 VideoThread/CameraThread 轮询
        self._result_queue = queue.Queue()

    def submit_frame(self, frame):
        """
        提交一帧到处理队列（非阻塞）。
        如果队列已满（上一帧还在处理中），丢弃旧帧，放入新帧。
        """
        try:
            self._frame_queue.put_nowait(frame)
        except queue.Full:
            try:
                self._frame_queue.get_nowait()  # 丢弃旧帧
                self._frame_queue.put_nowait(frame)  # 放入新帧
            except queue.Empty:
                pass

    def get_results(self):
        """
        非阻塞：获取所有待处理的识别结果。
        由 VideoThread/CameraThread 在主循环中调用，然后在自己的线程中发射 Qt 信号。
        :return: list of list（每次识别的一组结果）
        """
        results = []
        while True:
            try:
                result = self._result_queue.get_nowait()
                results.append(result)
            except queue.Empty:
                break
        return results

    def run(self):
        """处理循环：从队列取帧 → AI识别 → 业务处理 → 放入结果队列"""
        self._is_running = True

        while self._is_running:
            try:
                # 阻塞等待新帧，超时 200ms 后检查是否仍需运行
                frame = self._frame_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            # None 作为停止信号
            if frame is None:
                break

            self._frame_count += 1

            # 跳帧策略
            if self._frame_count % (self.skip_frames + 1) != 0:
                continue

            try:
                plates = self.process_frame(frame)  # AI识别（耗时操作）
                results = []
                for plate in plates:
                    result = self.handle_plate(plate)  # 业务处理
                    results.append(result)
                if results:
                    # 放入结果队列，而非发射 Qt 信号（避免跨线程事件循环问题）
                    self._result_queue.put(results)
            except Exception as e:
                print(f"[ProcessingThread] 识别异常: {e}")

    def stop(self):
        """安全停止线程"""
        self._is_running = False
        # 发送停止信号到队列
        try:
            self._frame_queue.put_nowait(None)
        except queue.Full:
            pass
        self.wait(3000)
