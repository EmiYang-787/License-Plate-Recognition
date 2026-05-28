"""
主界面模块 - 现代化深色主题
"""
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFileDialog, QMessageBox,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QFrame, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal, QSize
from PyQt5.QtGui import QImage, QPixmap, QColor, QPalette, QFont, QLinearGradient, QBrush, QPainter, QPen
import cv2


class ModernGroupBox(QGroupBox):
    """自定义现代化GroupBox"""
    def __init__(self, title, icon="", parent=None):
        super().__init__(parent)
        self.setTitle(f"{icon} {title}" if icon else title)
        self.setStyleSheet("""
            QGroupBox {
                font-size: 14px;
                font-weight: bold;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                padding: 15px;
                background-color: #2a2a2a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                color: #4fc3f7;
            }
        """)


class MainWindow(QMainWindow):
    manual_exit_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚗 智能车牌识别停车场系统")
        self.setMinimumSize(1400, 850)
        self._setup_palette()
        self._setup_ui()
        self._load_database_history()

    def _setup_palette(self):
        """设置全局深色调色板"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor("#1a1a2e"))
        dark_palette.setColor(QPalette.WindowText, QColor("#e0e0e0"))
        dark_palette.setColor(QPalette.Base, QColor("#16213e"))
        dark_palette.setColor(QPalette.AlternateBase, QColor("#1a1a2e"))
        dark_palette.setColor(QPalette.ToolTipBase, QColor("#4fc3f7"))
        dark_palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
        dark_palette.setColor(QPalette.Text, QColor("#e0e0e0"))
        dark_palette.setColor(QPalette.Button, QColor("#0f3460"))
        dark_palette.setColor(QPalette.ButtonText, QColor("#ffffff"))
        dark_palette.setColor(QPalette.BrightText, QColor("#ff6b6b"))
        dark_palette.setColor(QPalette.Highlight, QColor("#4fc3f7"))
        dark_palette.setColor(QPalette.HighlightedText, QColor("#1a1a2e"))
        self.setPalette(dark_palette)
        self.setStyleSheet("background-color: #1a1a2e;")

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        
        # 主布局
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ========== 左侧区域 ==========
        left_container = QWidget()
        left_container.setStyleSheet("background-color: #16213e; border-radius: 12px;")
        left_layout = QVBoxLayout(left_container)
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(20, 20, 20, 20)

        # 标题栏
        title_label = QLabel("📹 实时监控画面")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #4fc3f7;
                padding: 5px;
            }
        """)
        left_layout.addWidget(title_label)

        # 视频显示区域（带边框效果）
        video_frame = QFrame()
        video_frame.setStyleSheet("""
            QFrame {
                background-color: #0f0f23;
                border: 2px solid #3d3d3d;
                border-radius: 8px;
            }
        """)
        video_layout = QVBoxLayout(video_frame)
        video_layout.setContentsMargins(2, 2, 2, 2)
        
        self.video_label = QLabel("等待视频源...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(720, 540)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #0f0f23;
                color: #666;
                font-size: 16px;
                border-radius: 6px;
            }
        """)
        video_layout.addWidget(self.video_label)
        left_layout.addWidget(video_frame, stretch=1)

        # 统计信息栏
        stats_layout = QHBoxLayout()
        self.stats_total = self._create_stat_card("🚗 今日入场", "0")
        self.stats_active = self._create_stat_card("🅿️ 当前在场", "0")
        self.stats_revenue = self._create_stat_card("💰 今日收入", "¥0")
        stats_layout.addWidget(self.stats_total)
        stats_layout.addWidget(self.stats_active)
        stats_layout.addWidget(self.stats_revenue)
        left_layout.addLayout(stats_layout)

        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.btn_start_video = self._create_modern_button("📁 开始视频", "#4fc3f7")
        self.btn_open_camera = self._create_modern_button("📷 打开摄像头", "#6bcb77")
        self.btn_stop = self._create_modern_button("⏹ 停止", "#ff6b6b", enabled=False)
        
        btn_layout.addWidget(self.btn_start_video)
        btn_layout.addWidget(self.btn_open_camera)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addStretch()
        left_layout.addLayout(btn_layout)

        main_layout.addWidget(left_container, stretch=3)

        # ========== 右侧区域 ==========
        right_container = QWidget()
        right_container.setStyleSheet("background-color: #16213e; border-radius: 12px;")
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(20, 20, 20, 20)

        # 实时识别记录
        log_group = ModernGroupBox("实时识别记录", "📝")
        log_layout = QVBoxLayout(log_group)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("""
            QTextEdit {
                font-size: 13px;
                font-family: "Microsoft YaHei", "Consolas", monospace;
                background-color: #0f0f23;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                padding: 10px;
                line-height: 1.8;
            }
        """)
        log_layout.addWidget(self.result_text)
        right_layout.addWidget(log_group, stretch=2)

        # 手动出场
        manual_group = ModernGroupBox("手动出场", "🚪")
        manual_layout = QHBoxLayout(manual_group)

        self.manual_plate_input = QLineEdit()
        self.manual_plate_input.setPlaceholderText("输入车牌号，如：京A12345")
        self.manual_plate_input.setStyleSheet("""
            QLineEdit {
                font-size: 14px;
                padding: 12px;
                background-color: #0f0f23;
                color: #e0e0e0;
                border: 2px solid #3d3d3d;
                border-radius: 6px;
            }
            QLineEdit:focus {
                border-color: #4fc3f7;
            }
        """)

        self.btn_manual_exit = QPushButton("⏏️ 确认出场")
        self.btn_manual_exit.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                padding: 12px 24px;
                background-color: #e94560;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #ff6b6b; }
            QPushButton:pressed { background-color: #c73e54; }
        """)

        manual_layout.addWidget(self.manual_plate_input, stretch=1)
        manual_layout.addWidget(self.btn_manual_exit)
        right_layout.addWidget(manual_group)

        # 在场车辆表格
        table_group = ModernGroupBox("当前在场车辆", "🚗")
        table_layout = QVBoxLayout(table_group)

        self.table_active = QTableWidget()
        self.table_active.setColumnCount(3)
        self.table_active.setHorizontalHeaderLabels(["车牌号", "入场时间", "状态"])
        self.table_active.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_active.setStyleSheet("""
            QTableWidget {
                font-size: 13px;
                background-color: #0f0f23;
                color: #e0e0e0;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                gridline-color: #2a2a2a;
            }
            QHeaderView::section {
                background-color: #0f3460;
                color: #4fc3f7;
                padding: 10px;
                border: none;
                font-weight: bold;
                font-size: 13px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2a2a2a;
            }
            QTableWidget::item:selected {
                background-color: #4fc3f7;
                color: #1a1a2e;
            }
        """)
        self.table_active.verticalHeader().setVisible(False)
        self.table_active.setAlternatingRowColors(True)
        table_layout.addWidget(self.table_active)
        right_layout.addWidget(table_group, stretch=2)

        # 状态栏
        self.status_label = QLabel("🟢 系统就绪 | 等待操作...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #6bcb77;
                font-size: 13px;
                padding: 10px;
                background-color: #0f0f23;
                border-radius: 6px;
                border-left: 4px solid #6bcb77;
            }
        """)
        right_layout.addWidget(self.status_label)

        main_layout.addWidget(right_container, stretch=2)

    def _create_stat_card(self, title, value):
        """创建统计卡片"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #0f0f23;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setSpacing(5)
        layout.setContentsMargins(15, 10, 15, 10)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #888; font-size: 12px;")
        
        value_label = QLabel(value)
        value_label.setStyleSheet("color: #4fc3f7; font-size: 20px; font-weight: bold;")
        value_label.setObjectName("value")
        
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card

    def _create_modern_button(self, text, color, enabled=True):
        """创建现代化按钮"""
        btn = QPushButton(text)
        btn.setEnabled(enabled)
        btn.setStyleSheet(f"""
            QPushButton {{
                font-size: 14px;
                padding: 12px 24px;
                border-radius: 8px;
                background-color: {color};
                color: white;
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._lighten_color(color, 20)};
            }}
            QPushButton:pressed {{
                background-color: {self._darken_color(color, 20)};
            }}
            QPushButton:disabled {{
                background-color: #555;
                color: #888;
            }}
        """)
        return btn

    def _lighten_color(self, hex_color, percent):
        """颜色变亮"""
        c = QColor(hex_color)
        h, s, l, a = c.getHslF()
        l = min(1.0, l + percent / 100)
        c.setHslF(h, s, l, a)
        return c.name()

    def _darken_color(self, hex_color, percent):
        """颜色变暗"""
        c = QColor(hex_color)
        h, s, l, a = c.getHslF()
        l = max(0.0, l - percent / 100)
        c.setHslF(h, s, l, a)
        return c.name()

    def _load_database_history(self):
        """启动时从数据库恢复数据"""
        try:
            from database.vehicle_dao import VehicleDAO
            
            active_vehicles = VehicleDAO.get_active_vehicles()
            for vehicle in active_vehicles:
                self._add_active_vehicle(vehicle["plate"], vehicle["entry_time"])
            
            history = VehicleDAO.get_history(limit=20)
            for record in reversed(history):
                self._append_history_record(dict(record))
            
            # 更新统计
            self._update_stats()
            
            count = len(active_vehicles)
            if count > 0:
                self.update_status(f"✅ 已恢复 {count} 辆在场车辆")
            else:
                self.update_status("✅ 系统就绪 | 数据库已连接")
                
        except Exception as e:
            print(f"[MainWindow] 加载数据库历史失败: {e}")
            self.update_status("⚠️ 数据库加载失败")

    def _update_stats(self):
        """更新统计卡片"""
        try:
            from database.vehicle_dao import VehicleDAO
            
            active = len(VehicleDAO.get_active_vehicles())
            history = VehicleDAO.get_history(limit=1000)
            today = datetime.now().strftime("%Y-%m-%d")
            today_entries = len([h for h in history if h["entry_time"].startswith(today)])
            
            # 更新统计卡片
            cards = [self.stats_total, self.stats_active]
            for card in cards:
                labels = card.findChildren(QLabel)
                if len(labels) >= 2:
                    title = labels[0].text()
                    value_label = labels[1]
                    if "入场" in title:
                        value_label.setText(str(today_entries))
                    elif "在场" in title:
                        value_label.setText(str(active))
                        
        except Exception as e:
            print(f"[MainWindow] 更新统计失败: {e}")

    # ========== 公共接口 ==========

    @pyqtSlot(object)
    def update_frame(self, frame):
        if frame is None:
            return

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w

        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(qt_image)

        scaled = pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.video_label.setPixmap(scaled)

    @pyqtSlot(list)
    def update_results(self, results):
        for data in results:
            self._append_single_result(data)
        self._update_stats()

    def _append_single_result(self, data: dict, is_history: bool = False):
        plate = data.get("plate", "未知")
        status = data.get("status", "")
        time_str = data.get("time", "")
        duration = data.get("duration")

        if status not in ("entry", "exit"):
            return

        suffix = " <span style='color:#666; font-size:11px;'>(历史)</span>" if is_history else ""

        if status == "entry":
            msg = (f'<div style="margin:4px 0;">'
                   f'<span style="color:#6bcb77; font-weight:bold;">[{time_str}] 🚗 车辆入场</span> | '
                   f'车牌: <span style="color:#4fc3f7; font-weight:bold;">{plate}</span>{suffix}</div>')
            if not is_history:
                self._add_active_vehicle(plate, time_str)
        elif status == "exit":
            if duration is not None:
                msg = (f'<div style="margin:4px 0;">'
                       f'<span style="color:#e94560; font-weight:bold;">[{time_str}] 🚙 车辆出场</span> | '
                       f'车牌: <span style="color:#4fc3f7; font-weight:bold;">{plate}</span> | '
                       f'停车时长: <span style="color:#ffd93d; font-weight:bold;">{duration:.2f}</span> 小时{suffix}</div>')
            else:
                msg = (f'<div style="margin:4px 0;">'
                       f'<span style="color:#e94560; font-weight:bold;">[{time_str}] 🚙 车辆出场</span> | '
                       f'车牌: <span style="color:#4fc3f7; font-weight:bold;">{plate}</span>{suffix}</div>')
            if not is_history:
                self._remove_active_vehicle(plate)

        self.result_text.append(msg)

    def _append_history_record(self, record: dict):
        plate = record.get("plate_number", "")
        status = "exit" if record.get("status") == 1 else "entry"
        time_str = record.get("entry_time", "")
        duration = record.get("duration")
        
        data = {
            "plate": plate,
            "status": status,
            "time": time_str,
            "duration": duration
        }
        self._append_single_result(data, is_history=True)

    def _add_active_vehicle(self, plate: str, entry_time: str):
        for row in range(self.table_active.rowCount()):
            item = self.table_active.item(row, 0)
            if item and item.text() == plate:
                return
        
        row = self.table_active.rowCount()
        self.table_active.insertRow(row)
        
        plate_item = QTableWidgetItem(plate)
        plate_item.setForeground(QColor("#4fc3f7"))
        plate_item.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        
        time_item = QTableWidgetItem(entry_time)
        time_item.setForeground(QColor("#aaa"))
        
        status_item = QTableWidgetItem("在场")
        status_item.setForeground(QColor("#6bcb77"))
        status_item.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        
        self.table_active.setItem(row, 0, plate_item)
        self.table_active.setItem(row, 1, time_item)
        self.table_active.setItem(row, 2, status_item)

    def _remove_active_vehicle(self, plate: str):
        for row in range(self.table_active.rowCount()):
            item = self.table_active.item(row, 0)
            if item and item.text() == plate:
                self.table_active.removeRow(row)
                break

    @pyqtSlot(str)
    def update_status(self, text: str):
        self.status_label.setText(text)

    def get_video_path(self) -> str:
        path, _ = QFileDialog.getOpenFileName(
            self, "选择视频文件", "", "视频文件 (*.mp4 *.avi *.mkv *.mov);;所有文件 (*)"
        )
        return path

    def reset_ui_state(self):
        self.btn_start_video.setEnabled(True)
        self.btn_open_camera.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.video_label.setText("等待视频源...")
        self.video_label.setPixmap(QPixmap())

    def show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)