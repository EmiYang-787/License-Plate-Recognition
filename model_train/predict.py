from ultralytics import YOLO
import cv2
from pathlib import Path

def detect_single(image_path, model_path="runs/detect/plate_yolo11n/weights/best.pt"):
    """单张图片检测"""
    model = YOLO(model_path)
    results = model(image_path, save=True, conf=0.5, line_width=2)
    
    # 打印检测结果
    for r in results:
        boxes = r.boxes
        print(f"检测到 {len(boxes)} 个车牌")
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            conf = box.conf[0].cpu().numpy()
            print(f"  车牌 {i+1}: 坐标({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}), 置信度: {conf:.3f}")
    
    # 结果保存在 runs/detect/predict/ 下
    print(f"可视化结果保存在: {results[0].save_dir}")

def validate_model(model_path="runs/detect/plate_yolo11n/weights/best.pt"):
    """验证集评估"""
    model = YOLO(model_path)
    metrics = model.val(data="ccpd.yaml", split='val')
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.p.mean():.4f}")
    print(f"Recall: {metrics.box.r.mean():.4f}")

if __name__ == "__main__":
    # 验证模型
    # validate_model()
    
    # 单张测试（修改为你的测试图片路径）
    detect_single("datasets/ccpd/images/val/xxx.jpg")