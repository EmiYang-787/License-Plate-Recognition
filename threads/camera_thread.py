"""
摄像头实时处理线程
职责：读取摄像头帧 → 发送帧到UI显示 → 调用AI接口识别 → 发送结果
"""
from PyQt5.QtCore import QThread, pyqtSignal
import cv2


class CameraThread(QThread):
    frame_signal = pyqtSignal(object)       # 原始帧 → UI显示
    result_signal = pyqtSignal(list)        # 识别结果 → UI展示
    stopped_signal = pyqtSignal()

    def __init__(self, process_frame_func, handle_plate_func,
                 camera_id=0, parent=None, skip_frames=2):
        """
        :param process_frame_func: AI接口 process_frame(frame) → List[str]
        :param handle_plate_func: 业务接口 handle_plate(plate) → dict
        :param camera_id: 摄像头设备ID，默认0
        :param skip_frames: 跳帧数
        """
        super().__init__(parent)
        self.camera_id = camera_id
        self.process_frame = process_frame_func
        self.handle_plate = handle_plate_func
        self.skip_frames = skip_frames
        self._is_running = False
        self._frame_count = 0

    def run(self):
        self._is_running = True
        cap = cv2.VideoCapture(self.camera_id)

        if not cap.isOpened():
            print(f"[CameraThread] 无法打开摄像头: {self.camera_id}")
            self.stopped_signal.emit()
            return

        while self._is_running:
            ret, frame = cap.read()
            if not ret:
                continue

            self._frame_count += 1

            # 1. 发送帧到UI
            self.frame_signal.emit(frame)

            # 2. 跳帧识别
            if self._frame_count % (self.skip_frames + 1) == 0:
                try:
                    plates = self.process_frame(frame)
                    results = []
                    for plate in plates:
                        result = self.handle_plate(plate)
                        results.append(result)
                    if results:
                        self.result_signal.emit(results)
                except Exception as e:
                    print(f"[CameraThread] 识别异常: {e}")

            self.msleep(33)

        cap.release()
        self.stopped_signal.emit()

    def stop(self):
        self._is_running = False
        self.wait(1500)