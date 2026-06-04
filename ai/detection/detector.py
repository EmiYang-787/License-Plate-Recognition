"""
车牌检测模块
优先使用YOLO，无专用模型时自动回退到OpenCV Haar级联分类器
"""
import cv2
import numpy as np
from pathlib import Path

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


class PlateDetector:

    def __init__(self, model_path=None, conf_threshold=0.5):
        self.conf_threshold = conf_threshold
        self.model = None
        self.cascade = None
        self._load_model(model_path)

    def _load_model(self, model_path):
        """加载检测模型"""
        # 尝试1：指定路径
        if model_path and Path(model_path).exists() and ULTRALYTICS_AVAILABLE:
            self.model = YOLO(model_path)
            print(f"[PlateDetector] 已加载模型: {model_path}")
            return

        # 尝试2：weights目录下的.pt文件
        local_weights = Path(__file__).parent / "weights"
        if local_weights.exists():
            pt_files = list(local_weights.glob("*.pt"))
            if pt_files and ULTRALYTICS_AVAILABLE:
                self.model = YOLO(str(pt_files[0]))
                print(f"[PlateDetector] 已加载本地模型: {pt_files[0]}")
                return

        # 尝试3：OpenCV Haar级联（零配置备选）
        cascade_path = cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml'
        if Path(cascade_path).exists():
            self.cascade = cv2.CascadeClassifier(cascade_path)
            print("[PlateDetector] 已加载OpenCV Haar级联分类器")
            return

        print("[PlateDetector] ❌ 无可用检测模型！")

    def detect(self, frame):
        if frame is None or frame.size == 0:
            return []

        if self.model is not None:
            return self._yolo_detect(frame)
        if self.cascade is not None:
            return self._haar_detect(frame)
        return []

    def _yolo_detect(self, frame):
        """YOLO检测"""
        results = self.model(frame, verbose=False)
        detections = []

        for result in results:
            boxes = result.boxes
            for box in boxes:
                conf = float(box.conf[0])
                if conf < self.conf_threshold:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append({
                    "bbox": [x1, y1, x2, y2],
                    "conf": conf
                })
        return detections

    def _haar_detect(self, frame):
        """Haar级联检测"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        plates = self.cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(60, 20),
            maxSize=(600, 200)
        )

        detections = []
        for (x, y, w, h) in plates:
            detections.append({
                "bbox": [x, y, x + w, y + h],
                "conf": 0.85
            })
        return detections

    def crop_plate(self, frame, bbox):
        """裁剪车牌区域"""
        x1, y1, x2, y2 = bbox
        margin = 5
        h, w = frame.shape[:2]
        x1 = max(0, x1 - margin)
        y1 = max(0, y1 - margin)
        x2 = min(w, x2 + margin)
        y2 = min(h, y2 + margin)
        return frame[y1:y2, x1:x2]