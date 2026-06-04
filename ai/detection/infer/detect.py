import cv2
import numpy as np
import os
from ultralytics import YOLO

class PlateDetector:
    def __init__(self):
        # 获取模型文件的绝对路径
        model_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        model_path = os.path.join(model_dir, 'models', 'yolov8n.pt')
        
        if not os.path.exists(model_path):
            # 如果本地模型不存在，使用YOLO自动下载
            model_path = 'yolov8n.pt'
        
        self.model = YOLO(model_path)
    
    def detect(self, frame):
        results = self.model(frame)
        plates = []
        
        for result in results:
            for box in result.boxes:
                # 检查是否是车牌相关类别（YOLO通用模型的类别中没有车牌，需要调整）
                # 这里我们检测所有目标，后续OCR会筛选
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])
                if confidence > 0.3:  # 降低置信度阈值，因为通用模型对车牌检测可能不够精确
                    plates.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': confidence
                    })
        
        return plates

def detect_plates(frame):
    detector = PlateDetector()
    return detector.detect(frame)