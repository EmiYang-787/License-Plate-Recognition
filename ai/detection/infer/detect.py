import cv2
import numpy as np
from ultralytics import YOLO

class PlateDetector:
    def __init__(self, model_path='best.pt'):
        self.model = YOLO(model_path)
    
    def detect(self, frame):
        results = self.model(frame)
        plates = []
        
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])
                if confidence > 0.5:
                    plates.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': confidence
                    })
        
        return plates

def detect_plates(frame):
    detector = PlateDetector()
    return detector.detect(frame)