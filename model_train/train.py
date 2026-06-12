from ultralytics import YOLO

def main():
    # 加载YOLO11预训练模型（笔记本推荐 nano 版，最小最快）
    model = YOLO("yolo11n.pt")
    
    # 训练参数
    results = model.train(
        data="ccpd.yaml",        # 数据集配置
        epochs=50,               # 训练轮数（笔记本可先设30测试）
        imgsz=640,               # 输入尺寸
        batch=4,                 # 根据显存调整：CPU/GTX1650设4，6G+显存可设8
        device=0,            # 有NVIDIA显卡改为 device=0；Mac M系列改为 device="mps"
        workers=4,               # 数据加载线程
        patience=10,             # 早停：10轮不提升自动停止
        save=True,               # 保存模型
        project="runs/detect",   # 结果保存目录
        name="plate_yolo11n",    # 实验名称
        exist_ok=True,           # 覆盖已有目录
        pretrained=True,         # 使用预训练权重
        optimizer="AdamW",       # 优化器
        lr0=0.001,               # 初始学习率
        lrf=0.01,                # 最终学习率
        momentum=0.937,          # SGD动量
        weight_decay=0.0005,     # 权重衰减
        warmup_epochs=3.0,       # 预热轮数
        box=7.5,                 # 框损失权重
        cls=0.5,                 # 分类损失权重
        dfl=1.5,                 # 分布焦点损失
        plots=True,              # 生成训练曲线图
    )
    
    print("训练完成！最佳模型保存在：", results.best)

if __name__ == "__main__":
    main()