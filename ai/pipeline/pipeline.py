import cv2
import numpy as np

# Test mode: set to False for real OCR recognition
_TEST_MODE = False
_TEST_PLATES = ["京A12345", "沪B88888", "粤C66666"]

# OCR instance cache
_ocr_instance = None


def _init_ocr():
    """Initialize OCR instance (lazy loading)"""
    global _ocr_instance
    if _ocr_instance is None:
        try:
            from paddleocr import PaddleOCR
            print("[pipeline] Initializing PaddleOCR...")
            try:
                _ocr_instance = PaddleOCR(use_angle_cls=True, lang='ch')
            except:
                _ocr_instance = PaddleOCR(lang='ch')
            print("[pipeline] PaddleOCR initialized successfully")
        except Exception as e:
            print("[pipeline] OCR initialization failed: {}".format(e))
            _ocr_instance = None
    return _ocr_instance


def process_frame(frame):
    """
    Main license plate recognition interface
    
    Input:
        frame: ndarray - Input image (OpenCV format)
    
    Output:
        result: List[dict] - List of recognized plates with bounding boxes
                Each dict contains: 'plate', 'bbox', 'confidence'
    """
    try:
        if _TEST_MODE:
            return _simulate_recognition(frame)
        
        # Use real OCR recognition
        ocr = _init_ocr()
        if ocr is None:
            print("[pipeline] OCR not initialized, returning empty list")
            return []
        
        try:
            result = ocr.ocr(frame, cls=True)
        except TypeError:
            result = ocr.ocr(frame)
        
        plate_results = []
        
        if result and len(result) > 0:
            for line in result:
                if line and len(line) > 0:
                    text = line[1][0]
                    confidence = line[1][1]
                    bbox = line[0]  # Bounding box coordinates
                    
                    if _is_valid_plate(text) and confidence > 0.8:
                        # Convert bbox to int coordinates
                        bbox_int = [[int(p[0]), int(p[1])] for p in bbox]
                        plate_results.append({
                            'plate': text,
                            'bbox': bbox_int,
                            'confidence': confidence
                        })
                        print("[pipeline] Recognized plate: {} (confidence: {:.2f})".format(text, confidence))
        
        return plate_results
            
    except Exception as e:
        print("[pipeline] Error: {}".format(e))
        if _TEST_MODE:
            return _simulate_recognition(frame)
        return []


def _simulate_recognition(frame):
    """Simulate license plate recognition for testing"""
    import random
    
    if random.random() > 0.5:
        plate = random.choice(_TEST_PLATES)
        
        # Generate random bounding box
        h, w = frame.shape[:2]
        bbox_w = 120
        bbox_h = 40
        x = random.randint(50, w - bbox_w - 50)
        y = random.randint(50, h - bbox_h - 50)
        
        bbox = [
            [x, y],
            [x + bbox_w, y],
            [x + bbox_w, y + bbox_h],
            [x, y + bbox_h]
        ]
        
        print("[pipeline] Simulated recognition: {}".format(plate))
        return [{
            'plate': plate,
            'bbox': bbox,
            'confidence': 0.95
        }]
    return []


def _is_valid_plate(text):
    """Validate Chinese license plate format"""
    import re
    
    provinces = '京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领'
    pattern = r'^[' + provinces + r'][A-Z][A-Z0-9]{5}$'
    
    return re.match(pattern, text) is not None


def draw_plates_on_frame(frame, plates):
    """
    Draw bounding boxes and plate numbers on the frame
    
    Input:
        frame: ndarray - Input image
        plates: List[dict] - List of plate results from process_frame
    
    Output:
        frame: ndarray - Image with drawn boxes
    """
    for plate_info in plates:
        plate = plate_info['plate']
        bbox = plate_info['bbox']
        confidence = plate_info.get('confidence', 0)
        
        # Draw bounding box
        pts = np.array(bbox, np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.polylines(frame, [pts], isClosed=True, color=(0, 255, 0), thickness=2)
        
        # Draw plate number
        text_position = (bbox[0][0], bbox[0][1] - 10)
        cv2.putText(frame, plate, text_position, 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        
        # Draw confidence
        conf_text = "Conf: {:.2f}".format(confidence)
        conf_position = (bbox[0][0], bbox[2][1] + 25)
        cv2.putText(frame, conf_text, conf_position,
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
    
    return frame