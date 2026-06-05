"""
停车场业务逻辑模块
核心：车辆入场/出场管理 + 防重复识别
"""
import time
from datetime import datetime
from threading import Lock

from database.db import init_db
from database.vehicle_dao import VehicleDAO


class ParkingManager:
    """
    停车管理器（单例）
    
    业务逻辑：
    - 第一次识别 → 入场
    - 第二次识别 → 出场 + 计算时间
    - 3秒内重复识别 → 忽略（防抖）
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 初始化数据库
        init_db()
        
        # 防抖缓存：记录最近处理的车牌和时间
        # 格式: {plate: last_process_timestamp}
        self._recent_plates = {}
        self._debounce_seconds = 3  # 防抖时间（秒）
        
        self._cache_lock = Lock()
        self._initialized = True
    
    def should_process(self, plate: str) -> bool:
        """
        防重复识别判断
        
        :param plate: 车牌号
        :return: True表示需要处理，False表示忽略（重复）
        """
        current_time = time.time()
        
        with self._cache_lock:
            last_time = self._recent_plates.get(plate, 0)
            
            if current_time - last_time < self._debounce_seconds:
                # 在防抖时间内，认为是重复识别
                return False
            
            # 更新处理时间
            self._recent_plates[plate] = current_time
            
            # 清理过期缓存（防止内存无限增长）
            self._clean_expired_cache(current_time)
            
            return True
    
    def _clean_expired_cache(self, current_time):
        """清理过期的防抖缓存"""
        expired = []
        for plate, ts in self._recent_plates.items():
            if current_time - ts > self._debounce_seconds * 2:
                expired.append(plate)
        for plate in expired:
            del self._recent_plates[plate]
    
    def handle_plate(self, plate: str) -> dict:
        """
        处理车牌（核心业务流程）
        
        :param plate: 车牌号
        :return: dict 处理结果
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Step 1: 防抖检查
        if not self.should_process(plate):
            return {
                "plate": plate,
                "status": "ignored",
                "time": now_str,
                "duration": None,
                "message": "重复识别，已忽略"
            }
        
        # Step 2: 查询是否已在场
        active_record = VehicleDAO.find_active_vehicle(plate)
        
        if active_record is None:
            # ====== 入场流程 ======
            record_id = VehicleDAO.insert_entry(plate)
            return {
                "plate": plate,
                "status": "entry",
                "time": now_str,
                "duration": None,
                "message": "车辆入场"
            }
        else:
            # ====== 出场流程 ======
            record_id, entry_time = active_record
            duration = VehicleDAO.update_exit(record_id, entry_time)
            
            return {
                "plate": plate,
                "status": "exit",
                "time": now_str,
                "duration": round(duration, 2),
                "message": f"车辆出场，停车{duration:.2f}小时"
            }
    
    def get_active_vehicles(self):
        """获取当前在场车辆列表"""
        return VehicleDAO.get_active_vehicles()
    
    def get_history(self, limit=100):
        """获取历史记录"""
        return VehicleDAO.get_history(limit)


# ========== 全局管理器实例 ==========
_manager = None


def get_manager():
    """获取全局ParkingManager实例"""
    global _manager
    if _manager is None:
        _manager = ParkingManager()
    return _manager


# ========== 核心接口（必须严格遵守）==========

def handle_plate(plate):
    """
    核心接口：处理车牌号，判断入场或出场
    
    :param plate: 车牌号 (str)
    :return: dict 处理结果
        {
            "plate": "京A12345",
            "status": "entry" | "exit" | "ignored",
            "time": "2026-05-09 14:30:00",
            "duration": None | float (小时)
        }
    """
    manager = get_manager()
    return manager.handle_plate(plate)