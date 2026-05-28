"""
主控制器模块
职责：连接UI与线程、调度AI接口与业务接口、管理系统生命周期
数据流：frame → process_frame → handle_plate → UI显示
"""
from PyQt5.QtCore import QObject, pyqtSlot

from ui.main_window import MainWindow
from threads.video_thread import VideoThread
from threads.camera_thread import CameraThread


class MainController(QObject):
    """
    控制器严格遵循接口规范：
      - AI接口: process_frame(frame) → List[str]     （成员A实现）
      - 业务接口: handle_plate(plate) → dict          （成员B实现）
    """

    def __init__(self, process_frame_func, handle_plate_func):
        """
        :param process_frame_func: 成员A提供的AI识别接口
        :param handle_plate_func: 成员B提供的业务处理接口
        """
        super().__init__()
        self.process_frame = process_frame_func
        self.handle_plate = handle_plate_func

        self.window = MainWindow()
        self.video_thread = None
        self.camera_thread = None

        self._connect_ui_signals()

    def _connect_ui_signals(self):
        """连接UI按钮事件"""
        self.window.btn_start_video.clicked.connect(self.on_start_video)
        self.window.btn_open_camera.clicked.connect(self.on_open_camera)
        self.window.btn_stop.clicked.connect(self.on_stop)
        
        # 手动出场信号
        self.window.manual_exit_signal.connect(self.on_manual_exit)
        self.window.btn_manual_exit.clicked.connect(self._on_manual_exit_clicked)
        self.window.manual_plate_input.returnPressed.connect(self._on_manual_exit_clicked)

    def _on_manual_exit_clicked(self):
        """手动出场按钮点击代理"""
        plate = self.window.manual_plate_input.text().strip().upper()
        if plate:
            self.window.manual_exit_signal.emit(plate)

    def show(self):
        self.window.show()

    # ========== 按钮响应 ==========

    @pyqtSlot()
    def on_start_video(self):
        """开始播放视频文件"""
        video_path = self.window.get_video_path()
        if not video_path:
            return

        self._stop_all_threads()

        self.window.update_status("正在播放视频...")
        self.window.btn_start_video.setEnabled(False)
        self.window.btn_open_camera.setEnabled(False)
        self.window.btn_stop.setEnabled(True)

        self.video_thread = VideoThread(
            video_path=video_path,
            process_frame_func=self.process_frame,
            handle_plate_func=self.handle_plate
        )

        self.video_thread.frame_signal.connect(self.window.update_frame)
        self.video_thread.result_signal.connect(self.window.update_results)
        self.video_thread.stopped_signal.connect(self._on_thread_stopped)

        self.video_thread.start()

    @pyqtSlot()
    def on_open_camera(self):
        """打开摄像头"""
        self._stop_all_threads()

        self.window.update_status("摄像头实时识别中...")
        self.window.btn_start_video.setEnabled(False)
        self.window.btn_open_camera.setEnabled(False)
        self.window.btn_stop.setEnabled(True)

        self.camera_thread = CameraThread(
            process_frame_func=self.process_frame,
            handle_plate_func=self.handle_plate,
            camera_id=0
        )

        self.camera_thread.frame_signal.connect(self.window.update_frame)
        self.camera_thread.result_signal.connect(self.window.update_results)
        self.camera_thread.stopped_signal.connect(self._on_thread_stopped)

        self.camera_thread.start()

    @pyqtSlot()
    def on_stop(self):
        """停止当前所有任务"""
        self._stop_all_threads()
        self.window.update_status("已停止")
        self.window.reset_ui_state()

    # ========== 手动出场 ==========

    @pyqtSlot(str)
    def on_manual_exit(self, plate: str):
        """处理手动出场"""
        try:
            # 先检查是否在场
            from database.vehicle_dao import VehicleDAO
            active = VehicleDAO.find_active_vehicle(plate)
            if active is None:
                self.window.update_status(f"⚠️ 车牌 {plate} 不在停车场内")
                return

            # 调用业务接口（会触发防抖，但手动操作间隔通常足够）
            result = self.handle_plate(plate)
            
            # 如果返回 ignored（3秒内重复），强制出场
            if result.get("status") == "ignored":
                from service.parking_service import handle_plate_force
                result = handle_plate_force(plate)
            
            # 显示结果
            self.window.update_results([result])
            self.window.update_status(f"✅ 车牌 {plate} 手动出场成功，停车 {result.get('duration', 0):.2f} 小时")
            
        except Exception as e:
            print(f"[Controller] 手动出场失败: {e}")
            self.window.update_status(f"❌ 手动出场失败: {e}")

    # ========== 线程管理 ==========

    def _stop_all_threads(self):
        """安全停止所有运行中的线程"""
        if self.video_thread and self.video_thread.isRunning():
            self.video_thread.frame_signal.disconnect(self.window.update_frame)
            self.video_thread.result_signal.disconnect(self.window.update_results)
            self.video_thread.stop()
            self.video_thread = None

        if self.camera_thread and self.camera_thread.isRunning():
            self.camera_thread.frame_signal.disconnect(self.window.update_frame)
            self.camera_thread.result_signal.disconnect(self.window.update_results)
            self.camera_thread.stop()
            self.camera_thread = None

    @pyqtSlot()
    def _on_thread_stopped(self):
        """线程自然结束回调（如视频播放完毕）"""
        self.window.reset_ui_state()
        self.window.update_status("播放结束")