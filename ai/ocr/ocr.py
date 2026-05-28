from paddleocr import PaddleOCR
import cv2

class PlateOCR:
    def __init__(self):
        self.ocr = PaddleOCR(use_angle_cls=True, lang='ch')
    
    def recognize(self, plate_image):
        result = self.ocr.ocr(plate_image, cls=True)
        if result and len(result) > 0:
            for line in result:
                if line and len(line) > 0:
                    text = line[1][0]
                    confidence = line[1][1]
                    if confidence > 0.8:
                        return text
        return None

def recognize_plate(plate_image):
    ocr = PlateOCR()
    return ocr.recognize(plate_image)