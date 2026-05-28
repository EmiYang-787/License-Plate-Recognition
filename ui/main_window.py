"""
主界面模块 - 现代化专业UI
"""
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QFrame, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QColor, QFont
import cv2

# ==================== 全局样式常量 ====================

STYLE_GLOBAL = """
QMainWindow {
    background-color: #0a0e1a;
}

QToolTip {
    background-color: #1e2a3a;
    color: #c0d0e0;
    border: 1px solid #2a3a4a;
    padding: 6px 10px;
    border-radius: 4px;
    font-size: 12px;
}
"""

STYLE_SCROLLBAR = """
QScrollBar:vertical {
    background: #0d1220;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #2a3a4a;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #3a4a5a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QScrollBar:horizontal {
    background: #0d1220;
    height: 8px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #2a3a4a;
    border-radius: 4px;
    min-width: 30px;
}
QScrollBar::handle:horizontal:hover {
    background: #3a4a5a;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0px;
}
"""


def _hex_to_rgba(hex_color, alpha=255):
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"


# ==================== 自定义组件 ====================

class _CardFrame(QFrame):
    """带阴影的卡片容器"""
    def __init__(self, parent=None, radius=12, bg="#111827"):
        super().__init__(parent)
        self.setStyleSheet(f"""
            _CardFrame {{
                background-color: {bg};
                border-radius: {radius}px;
                border: 1px solid #1e293b;
            }}
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)


class _SectionTitle(QFrame):
    """分区标题组件"""
    def __init__(self, icon, title, accent="#38bdf8", parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        dot = QFrame()
        dot.setFixedSize(4, 24)
        dot.setStyleSheet(f"""
            QFrame {{
                background-color: {accent};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(dot)

        label = QLabel(f"{icon}  {title}")
        label.setStyleSheet(f"""
            QLabel {{
                color: #e2e8f0;
                font-size: 15px;
                font-weight: 700;
                background: transparent;
                border: none;
            }}
        """)
        layout.addWidget(label)
        layout.addStretch()


class _StatCard(QFrame):
    """统计卡片"""
    def __init__(self, icon, title, accent="#38bdf8", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            _StatCard {{
                background-color: #0f172a;
                border-radius: 12px;
                border: 1px solid #1e293b;
            }}
        """)
        self.setFixedHeight(90)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        # 图标区
        icon_bg = QFrame()
        icon_bg.setFixedSize(48, 48)
        icon_bg.setStyleSheet(f"""
            QFrame {{
                background-color: {_hex_to_rgba(accent, 25)};
                border-radius: 12px;
            }}
        """)
        icon_layout = QVBoxLayout(icon_bg)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 20px; background: transparent; border: none;")
        icon_layout.addWidget(icon_label)
        layout.addWidget(icon_bg)

        # 文字区
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #64748b; font-size: 12px; background: transparent; border: none;")

        self.value_label = QLabel("0")
        self.value_label.setStyleSheet(f"color: {accent}; font-size: 22px; font-weight: 800; background: transparent; border: none;")

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.value_label)
        layout.addLayout(text_layout)
        layout.addStretch()


class _ActionButton(QPushButton):
    """统一样式的操作按钮"""
    def __init__(self, icon, text, accent="#38bdf8", parent=None):
        super().__init__(f"  {icon}  {text}", parent)
        self._accent = QColor(accent)
        self._accent_text = accent
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(44)
        self.setStyleSheet(f"""
            _ActionButton {{
                font-size: 13px;
                font-weight: 600;
                padding: 10px 20px;
                border-radius: 10px;
                background-color: {_hex_to_rgba(accent, 25)};
                color: {accent};
                border: 1px solid {_hex_to_rgba(accent, 40)};
            }}
            _ActionButton:hover {{
                background-color: {_hex_to_rgba(accent, 40)};
                border-color: {_hex_to_rgba(accent, 60)};
            }}
            _ActionButton:pressed {{
                background-color: {_hex_to_rgba(accent, 20)};
            }}
            _ActionButton:disabled {{
                background-color: #1a1e2e;
                color: #475569;
                border-color: #1e293b;
            }}
        """)


# ==================== 主窗口 ====================

class MainWindow(QMainWindow):
    manual_exit_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能车牌识别停车场系统")
        self.setMinimumSize(1400, 860)
        self.setStyleSheet(STYLE_GLOBAL)
        self._setup_ui()
        self._load_database_history()

    # ==================== UI构建 ====================

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setSpacing(16)
        root.setContentsMargins(16, 16, 16, 16)

        # ---- 左侧面板 ----
        left_panel = self._build_left_panel()
        root.addWidget(left_panel, stretch=3)

        # ---- 右侧面板 ----
        right_panel = self._build_right_panel()
        root.addWidget(right_panel, stretch=2)

    def _build_left_panel(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(14)
        layout.setContentsMargins(0, 0, 0, 0)

        # 监控标题
        layout.addWidget(_SectionTitle("\U0001f4f9", "实时监控画面", "#38bdf8"))

        # 视频显示区
        video_card = _CardFrame(radius=14, bg="#0c1222")
        video_inner = QVBoxLayout(video_card)
        video_inner.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel("等待视频源...")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(720, 520)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #060b14;
                color: #334155;
                font-size: 15px;
                border-radius: 14px;
                font-weight: 500;
            }
        """)
        video_inner.addWidget(self.video_label)
        layout.addWidget(video_card, stretch=1)

        # 统计卡片行
        stats = QHBoxLayout()
        stats.setSpacing(12)

        self.stats_total = _StatCard("\U0001f698", "今日入场", "#38bdf8")
        self.stats_active = _StatCard("\U0001f17f", "当前在场", "#34d399")
        self.stats_revenue = _StatCard("\U0001f4b0", "今日收入", "#f59e0b")

        stats.addWidget(self.stats_total)
        stats.addWidget(self.stats_active)
        stats.addWidget(self.stats_revenue)
        layout.addLayout(stats)

        # 控制按钮行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_start_video = _ActionButton("\U0001f4c1", "选择视频", "#38bdf8")
        self.btn_open_camera = _ActionButton("\U0001f4f7", "打开摄像头", "#34d399")
        self.btn_stop = _ActionButton("⏹", "停止", "#ef4444")
        self.btn_stop.setEnabled(False)

        btn_row.addWidget(self.btn_start_video)
        btn_row.addWidget(self.btn_open_camera)
        btn_row.addWidget(self.btn_stop)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        return container

    def _build_right_panel(self) -> QWidget:
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        # ---- 识别记录 ----
        layout.addWidget(_SectionTitle("\U0001f4dd", "实时识别记录", "#38bdf8"))

        log_card = _CardFrame(radius=12, bg="#0c1222")
        log_inner = QVBoxLayout(log_card)
        log_inner.setContentsMargins(10, 10, 10, 10)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet(f"""
            QTextEdit {{
                font-size: 13px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
                background-color: #060b14;
                color: #cbd5e1;
                border: 1px solid #1e293b;
                border-radius: 8px;
                padding: 12px;
                line-height: 1.9;
            }}
            {STYLE_SCROLLBAR}
        """)
        log_inner.addWidget(self.result_text)
        layout.addWidget(log_card, stretch=2)

        # ---- 手动出场 ----
        layout.addWidget(_SectionTitle("\U0001f6aa", "手动出场", "#f59e0b"))

        manual_card = _CardFrame(radius=12, bg="#0c1222")
        manual_inner = QHBoxLayout(manual_card)
        manual_inner.setContentsMargins(14, 12, 14, 12)
        manual_inner.setSpacing(10)

        self.manual_plate_input = QLineEdit()
        self.manual_plate_input.setPlaceholderText("输入车牌号，如：京A12345")
        self.manual_plate_input.setMinimumHeight(44)
        self.manual_plate_input.setStyleSheet(f"""
            QLineEdit {{
                font-size: 14px;
                padding: 10px 14px;
                background-color: #060b14;
                color: #e2e8f0;
                border: 1px solid #1e293b;
                border-radius: 10px;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }}
            QLineEdit:focus {{
                border-color: #f59e0b;
                background-color: #0c1222;
            }}
            QLineEdit::placeholder {{
                color: #475569;
            }}
        """)

        self.btn_manual_exit = QPushButton("  确认出场")
        self.btn_manual_exit.setCursor(Qt.PointingHandCursor)
        self.btn_manual_exit.setMinimumHeight(44)
        self.btn_manual_exit.setStyleSheet("""
            QPushButton {
                font-size: 14px;
                font-weight: 700;
                padding: 10px 20px;
                background-color: #b91c1c;
                color: #fecaca;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #dc2626;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #991b1b;
            }
        """)

        manual_inner.addWidget(self.manual_plate_input, stretch=1)
        manual_inner.addWidget(self.btn_manual_exit)
        layout.addWidget(manual_card)

        # ---- 在场车辆表格 ----
        layout.addWidget(_SectionTitle("\U0001f698", "当前在场车辆", "#34d399"))

        table_card = _CardFrame(radius=12, bg="#0c1222")
        table_inner = QVBoxLayout(table_card)
        table_inner.setContentsMargins(10, 10, 10, 10)

        self.table_active = QTableWidget()
        self.table_active.setColumnCount(3)
        self.table_active.setHorizontalHeaderLabels(["车牌号", "入场时间", "状态"])
        self.table_active.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_active.setStyleSheet(f"""
            QTableWidget {{
                font-size: 13px;
                background-color: #060b14;
                color: #cbd5e1;
                border: 1px solid #1e293b;
                border-radius: 8px;
                gridline-color: #1a1f2e;
                font-family: "Microsoft YaHei", "Segoe UI", sans-serif;
            }}
            QHeaderView::section {{
                background-color: #0f172a;
                color: #94a3b8;
                padding: 10px 8px;
                border: none;
                border-bottom: 2px solid #1e293b;
                font-weight: 700;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            QTableWidget::item {{
                padding: 10px 8px;
                border-bottom: 1px solid #1a1f2e;
            }}
            QTableWidget::item:selected {{
                background-color: #1e3a5f;
                color: #e2e8f0;
            }}
            QTableWidget::item:hover {{
                background-color: #11192b;
            }}
            {STYLE_SCROLLBAR}
        """)
        self.table_active.verticalHeader().setVisible(False)
        self.table_active.setAlternatingRowColors(True)
        self.table_active.setShowGrid(False)
        table_inner.addWidget(self.table_active)
        layout.addWidget(table_card, stretch=2)

        # ---- 状态栏 ----
        self.status_label = QLabel("\U0001f7e2  系统就绪 | 等待操作...")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #34d399;
                font-size: 13px;
                padding: 10px 14px;
                background-color: #0c1222;
                border-radius: 8px;
                border-left: 4px solid #34d399;
                font-weight: 500;
            }
        """)
        layout.addWidget(self.status_label)

        return container

    # ==================== 公共接口（保持不变） ====================

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

    # ==================== 内部逻辑（保持不变） ====================

    def _append_single_result(self, data: dict, is_history: bool = False):
        plate = data.get("plate", "未知")
        status = data.get("status", "")
        time_str = data.get("time", "")
        duration = data.get("duration")

        if status not in ("entry", "exit"):
            return

        suffix = " <span style='color:#475569; font-size:11px;'>(历史)</span>" if is_history else ""

        if status == "entry":
            msg = (f'<div style="margin:4px 0;">'
                   f'<span style="color:#34d399; font-weight:bold;">[{time_str}] \U0001f698 车辆入场</span> | '
                   f'车牌: <span style="color:#38bdf8; font-weight:bold;">{plate}</span>{suffix}</div>')
            if not is_history:
                self._add_active_vehicle(plate, time_str)
        elif status == "exit":
            if duration is not None:
                msg = (f'<div style="margin:4px 0;">'
                       f'<span style="color:#ef4444; font-weight:bold;">[{time_str}] \U0001f699 车辆出场</span> | '
                       f'车牌: <span style="color:#38bdf8; font-weight:bold;">{plate}</span> | '
                       f'停车时长: <span style="color:#f59e0b; font-weight:bold;">{duration:.2f}</span> 小时{suffix}</div>')
            else:
                msg = (f'<div style="margin:4px 0;">'
                       f'<span style="color:#ef4444; font-weight:bold;">[{time_str}] \U0001f699 车辆出场</span> | '
                       f'车牌: <span style="color:#38bdf8; font-weight:bold;">{plate}</span>{suffix}</div>')
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
        plate_item.setForeground(QColor("#38bdf8"))
        plate_item.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))

        time_item = QTableWidgetItem(entry_time)
        time_item.setForeground(QColor("#94a3b8"))

        status_item = QTableWidgetItem("●  在场")
        status_item.setForeground(QColor("#34d399"))
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

    def _load_database_history(self):
        try:
            from database.vehicle_dao import VehicleDAO

            active_vehicles = VehicleDAO.get_active_vehicles()
            for vehicle in active_vehicles:
                self._add_active_vehicle(vehicle["plate"], vehicle["entry_time"])

            history = VehicleDAO.get_history(limit=20)
            for record in reversed(history):
                self._append_history_record(dict(record))

            self._update_stats()

            count = len(active_vehicles)
            if count > 0:
                self.update_status(f"✅  已恢复 {count} 辆在场车辆")
            else:
                self.update_status("✅  系统就绪 | 数据库已连接")

        except Exception as e:
            print(f"[MainWindow] 加载数据库历史失败: {e}")
            self.update_status("⚠️  数据库加载失败")

    def _update_stats(self):
        try:
            from database.vehicle_dao import VehicleDAO

            active = len(VehicleDAO.get_active_vehicles())
            history = VehicleDAO.get_history(limit=1000)
            today = datetime.now().strftime("%Y-%m-%d")
            today_entries = len([h for h in history if h["entry_time"].startswith(today)])

            for card in [self.stats_total, self.stats_active]:
                title_label = card.title_label
                if title_label:
                    title = title_label.text()
                    if "入场" in title:
                        card.value_label.setText(str(today_entries))
                    elif "在场" in title:
                        card.value_label.setText(str(active))

        except Exception as e:
            print(f"[MainWindow] 更新统计失败: {e}")
