"""
系统入口 - 启动时立即初始化模型和数据库
"""
import sys
import os

# 禁用 oneDNN 警告（可选）
os.environ['FLAGS_use_mkldnn'] = '0'

from PyQt5.QtWidgets import QApplication

# ========== 启动时立即初始化 ==========
print("[Main] 正在初始化系统...")

# 1. 初始化 AI 模型（成员A）
from ai.pipeline.pipeline import get_pipeline
pipeline = get_pipeline()  # ← 立即创建，加载 YOLO 模型
print("[Main] AI 模型加载完成")

# 2. 初始化数据库（成员B）
from service.parking_service import get_manager
manager = get_manager()  # ← 立即创建，初始化 SQLite
print("[Main] 数据库初始化完成")

# 3. 导入 Controller
from controller.main_controller import MainController

# 注入已初始化的接口
from ai.pipeline.pipeline import process_frame
from service.parking_service import handle_plate
# =====================================


def main():
    app = QApplication(sys.argv)
    
    controller = MainController(
        process_frame_func=process_frame,
        handle_plate_func=handle_plate
    )
    
    controller.show()
    print("[Main] 系统启动完成，界面已显示")
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()