import os
import cv2
import numpy as np
from pathlib import Path
import shutil
import random

def parse_ccpd_corners(filename):
    """
    CCPD文件名格式: ..._x1&y1_x2&y2_x3&y3_x4&y4_...
    角点信息在倒数第二个-和最后一个-之间
    """
    try:
        parts = filename.split('-')
        if len(parts) < 4:
            return None
        
        # 倒数第二部分是角点信息
        corner_part = parts[-2]
        # 替换 & 为 _ 然后分割
        corner_part = corner_part.replace('&', '_')
        coords = list(map(int, corner_part.split('_')))
        
        if len(coords) < 8:
            return None
            
        # 四个角点坐标 [x1,y1, x2,y2, x3,y3, x4,y4]
        pts = np.array(coords[:8]).reshape(4, 2)
        return pts
    except Exception as e:
        print(f"解析失败: {filename}, 错误: {e}")
        return None

def ccpd_to_yolo_label(img_path, label_dir):
    """将单张CCPD图片转为YOLO标签"""
    img_path = Path(img_path)
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"无法读取图片: {img_path}")
        return False
    
    h, w = img.shape[:2]
    pts = parse_ccpd_corners(img_path.name)
    if pts is None:
        return False
    
    # 计算最小外接矩形
    x_min, y_min = pts.min(axis=0)
    x_max, y_max = pts.max(axis=0)
    
    # 边界检查
    x_min, y_min = max(0, x_min), max(0, y_min)
    x_max, y_max = min(w, x_max), min(h, y_max)
    
    # 转为YOLO格式（归一化中心点+宽高）
    x_center = (x_min + x_max) / 2.0 / w
    y_center = (y_min + y_max) / 2.0 / h
    bw = (x_max - x_min) / float(w)
    bh = (y_max - y_min) / float(h)
    
    # 限制在0-1之间
    x_center = max(0, min(1, x_center))
    y_center = max(0, min(1, y_center))
    bw = max(0, min(1, bw))
    bh = max(0, min(1, bh))
    
    # 写入标签（类别0：车牌）
    label_path = Path(label_dir) / f"{img_path.stem}.txt"
    with open(label_path, 'w', encoding='utf-8') as f:
        f.write(f"0 {x_center:.6f} {y_center:.6f} {bw:.6f} {bh:.6f}\n")
    
    return True

def split_dataset(src_dir, dst_dir, train_ratio=0.9):
    """
    自动划分训练集和验证集
    src_dir: 原始CCPD图片所在目录（所有图片混在一起）
    dst_dir: 目标目录（datasets/ccpd）
    """
    src_dir = Path(src_dir)
    dst_dir = Path(dst_dir)
    
    # 创建目录
    (dst_dir / "images/train").mkdir(parents=True, exist_ok=True)
    (dst_dir / "images/val").mkdir(parents=True, exist_ok=True)
    (dst_dir / "labels/train").mkdir(parents=True, exist_ok=True)
    (dst_dir / "labels/val").mkdir(parents=True, exist_ok=True)
    
    # 获取所有jpg图片
    all_images = list(src_dir.glob("*.jpg")) + list(src_dir.glob("*.png"))
    random.shuffle(all_images)
    
    split_idx = int(len(all_images) * train_ratio)
    train_images = all_images[:split_idx]
    val_images = all_images[split_idx:]
    
    print(f"总图片数: {len(all_images)}")
    print(f"训练集: {len(train_images)}, 验证集: {len(val_images)}")
    
    # 处理训练集
    success_train = 0
    for img_path in train_images:
        # 复制/移动到目标目录
        dst_img = dst_dir / "images/train" / img_path.name
        shutil.copy2(str(img_path), str(dst_img))
        
        if ccpd_to_yolo_label(dst_img, dst_dir / "labels/train"):
            success_train += 1
        else:
            # 如果标签生成失败，删除图片
            dst_img.unlink()
    
    # 处理验证集
    success_val = 0
    for img_path in val_images:
        dst_img = dst_dir / "images/val" / img_path.name
        shutil.copy2(str(img_path), str(dst_img))
        
        if ccpd_to_yolo_label(dst_img, dst_dir / "labels/val"):
            success_val += 1
        else:
            dst_img.unlink()
    
    print(f"成功生成 - 训练集: {success_train}, 验证集: {success_val}")

if __name__ == "__main__":
    # 使用示例：
    # 假设你下载的CCPD图片都在 downloads/ccpd/ 目录下
    # 运行后会自动划分到 datasets/ccpd/
    
    SRC_PATH = "downloads/ccpd"  # ← 修改为你下载的CCPD图片路径
    DST_PATH = "datasets/ccpd"
    
    if not Path(SRC_PATH).exists():
        print(f"错误：源目录 {SRC_PATH} 不存在！")
        print("请将下载的CCPD图片放到一个文件夹，然后修改 SRC_PATH")
    else:
        split_dataset(SRC_PATH, DST_PATH, train_ratio=0.9)