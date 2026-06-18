"""
停车场业务逻辑模块
核心：车辆入场/出场管理 + 防重复识别 + 状态锁定 + 最短停车时长 + 计费
"""
import math
import time
import re
from datetime import datetime
from threading import Lock

from database.db import init_db


def calculate_fee(duration_hours: float) -> float:
    """
    计算停车费用
    规则：前2小时免费，超过2小时后每小时10元，不满一小时按一小时算
    """
    if duration_hours <= 2:
        return 0.0
    chargeable = math.ceil(duration_hours - 2)  # 不满一小时按一小时
    return chargeable * 10.0
from database.vehicle_dao import VehicleDAO


def _validate_plate(plate: str) -> bool:
    """验证车牌格式（与OCR模块保持一致）"""
    if not plate or len(plate) < 7:
        return False

    # 标准蓝牌：严格7字符。省份+城市字母+4位字母数字+1位后缀
    pattern_normal = r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-HJ-NP-Z][A-HJ-NP-Z0-9]{4}[A-Z0-9挂学警港澳]$'
    # 新能源绿牌：严格8字符。省份+城市字母+D/F+5位字母数字
    pattern_new_energy = r'^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼][A-HJ-NP-Z][DF][A-HJ-NP-Z0-9]{5}$'
    # 使馆车牌
    pattern_embassy = r'^使\d{6}$'
    # 武警车牌
    pattern_wujing = r'^WJ[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼]?\d{4,5}[A-Z]?$'

    for pattern in [pattern_normal, pattern_new_energy, pattern_embassy, pattern_wujing]:
        if re.match(pattern, plate):
            return True
    return False


class ParkingManager:
    """
    停车管理器（单例）

    业务逻辑：
    - 10秒内重复识别 → 忽略（防抖，适配视频流）
    - 120秒内状态锁定 → 不切换入场/出场
    - 最短停车60秒 → 入场后60秒内不触发出场（防误识别导致立即出库）
    - 出场后120秒内不入场 → 防止同一辆车反复出入库
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

        init_db()

        # 防抖缓存：5秒（避免视频流同一车辆重复触发）
        self._recent_plates = {}
        self._debounce_seconds = 5

        # 状态锁定缓存：45秒内不切换出入场状态（足够覆盖车辆驶离画面的时间）
        self._status_lock = {}  # {plate: (status, timestamp)}
        self._lock_seconds = 45

        # ====== 最短停车时长（秒）======
        # 入场后15秒内不触发出场，防止OCR波动导致立即入库后即出库
        self._min_parking_seconds = 15
        self._entry_timestamps = {}
        # =====================================

        # ====== 最近出场缓存 ======
        # 出场后30秒内不允许再次入场（防止同一车辆被反复识别入场）
        self._recently_exited = {}  # {plate: exit_timestamp}
        self._reentry_block_seconds = 30
        # =====================================

        self._cache_lock = Lock()
        self._initialized = True

    def should_process(self, plate: str) -> bool:
        """10秒防抖"""
        current_time = time.time()

        with self._cache_lock:
            last_time = self._recent_plates.get(plate, 0)
            if current_time - last_time < self._debounce_seconds:
                return False

            self._recent_plates[plate] = current_time
            return True

    def _get_locked_status(self, plate: str):
        """
        获取锁定状态
        :return: (status, remaining_seconds) 或 (None, 0)
        """
        current_time = time.time()
        locked = self._status_lock.get(plate)

        if locked:
            status, timestamp = locked
            remaining = self._lock_seconds - (current_time - timestamp)
            if remaining > 0:
                return status, int(remaining)

        return None, 0

    def _set_locked_status(self, plate: str, status: str):
        """设置锁定状态"""
        self._status_lock[plate] = (status, time.time())

    def _is_recently_exited(self, plate: str) -> bool:
        """检查是否最近刚出场（防止立即重新入场）"""
        current_time = time.time()
        exit_time = self._recently_exited.get(plate, 0)
        if current_time - exit_time < self._reentry_block_seconds:
            return True
        # 清理过期记录
        if exit_time > 0:
            del self._recently_exited[plate]
        return False

    def _get_min_parking_remaining(self, plate: str) -> int:
        """获取最短停车剩余时间（秒）"""
        current_time = time.time()
        entry_time = self._entry_timestamps.get(plate, 0)
        if entry_time == 0:
            return 0
        elapsed = current_time - entry_time
        remaining = self._min_parking_seconds - elapsed
        return max(0, int(remaining))

    def handle_plate(self, plate: str) -> dict:
        """
        处理车牌（核心业务流程）
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_time = time.time()

        # Step 1: 10秒防抖检查
        if not self.should_process(plate):
            return {
                "plate": plate,
                "status": "ignored",
                "time": now_str,
                "duration": None,
                "message": "重复识别，已忽略"
            }

        # Step 2: 检查是否最近刚出场（防止反复出入库）
        if self._is_recently_exited(plate):
            return {
                "plate": plate,
                "status": "ignored",
                "time": now_str,
                "duration": None,
                "message": "车辆近期已出场，暂不允许重新入场"
            }

        # Step 3: 查询是否已在场
        active_record = VehicleDAO.find_active_vehicle(plate)
        current_db_status = "in" if active_record else "out"

        # Step 4: 检查状态锁定
        locked_status, remaining = self._get_locked_status(plate)

        if locked_status is not None:
            # 120秒内状态锁定，保持当前状态不变
            if locked_status == "entry" and current_db_status == "in":
                # 锁定为入场，且当前在场 → 忽略，保持入场状态
                return {
                    "plate": plate,
                    "status": "ignored",
                    "time": now_str,
                    "duration": None,
                    "message": f"车辆处于入场锁定状态，还剩{remaining}秒"
                }
            elif locked_status == "exit" and current_db_status == "out":
                # 锁定为出场，且当前不在场 → 忽略，保持出场状态
                return {
                    "plate": plate,
                    "status": "ignored",
                    "time": now_str,
                    "duration": None,
                    "message": f"车辆处于出场锁定状态，还剩{remaining}秒"
                }

        # Step 5: 无锁定或锁定已过期，正常处理
        if active_record is None:
            # ====== 入场流程 ======
            # 再次检查最近出场（双重保险）
            if self._is_recently_exited(plate):
                return {
                    "plate": plate,
                    "status": "ignored",
                    "time": now_str,
                    "duration": None,
                    "message": "车辆近期已出场，暂不允许重新入场"
                }

            record_id = VehicleDAO.insert_entry(plate)
            self._set_locked_status(plate, "entry")  # 锁定为入场状态
            self._entry_timestamps[plate] = current_time  # 记录入场时间
            return {
                "plate": plate,
                "status": "entry",
                "time": now_str,
                "duration": None,
                "message": "车辆入场"
            }
        else:
            # ====== 出场流程 ======
            # 检查最短停车时长
            min_remaining = self._get_min_parking_remaining(plate)
            if min_remaining > 0:
                return {
                    "plate": plate,
                    "status": "ignored",
                    "time": now_str,
                    "duration": None,
                    "message": f"停车时间不足，还需{min_remaining}秒才可出场"
                }

            record_id, entry_time = active_record
            # 先算时长再算费，一次写入数据库
            entry_dt = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
            duration = (datetime.now() - entry_dt).total_seconds() / 3600
            fee = calculate_fee(duration)
            VehicleDAO.update_exit(record_id, entry_time, fee)
            self._set_locked_status(plate, "exit")  # 锁定为出场状态
            self._recently_exited[plate] = current_time  # 记录出场时间
            # 清理入场时间戳
            self._entry_timestamps.pop(plate, None)
            fee_str = f"{fee:.0f}元" if fee > 0 else "免费"
            return {
                "plate": plate,
                "status": "exit",
                "time": now_str,
                "duration": round(duration, 2),
                "fee": fee,
                "message": f"车辆出场，停车{duration:.2f}小时，费用：{fee_str}"
            }

    def get_active_vehicles(self):
        return VehicleDAO.get_active_vehicles()

    def get_history(self, limit=100):
        return VehicleDAO.get_history(limit)


# ========== 全局管理器实例 ==========
_manager = None


def get_manager():
    global _manager
    if _manager is None:
        _manager = ParkingManager()
    return _manager


# ========== 核心接口 ==========

def handle_plate(plate):
    if not _validate_plate(plate):
        return {
            "plate": plate,
            "status": "invalid",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration": None,
            "message": "车牌格式不合法"
        }

    manager = get_manager()
    return manager.handle_plate(plate)


def handle_plate_force(plate: str) -> dict:
    """强制出场（手动出场），绕过最短停车时长限制，但不绕过状态锁定"""
    if not _validate_plate(plate):
        return {
            "plate": plate,
            "status": "invalid",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duration": None,
            "message": "车牌格式不合法"
        }

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    manager = get_manager()

    # 查询是否在场
    active_record = VehicleDAO.find_active_vehicle(plate)

    if active_record is None:
        return {
            "plate": plate,
            "status": "ignored",
            "time": now_str,
            "duration": None,
            "message": "车辆不在停车场内"
        }

    # 检查状态锁定
    locked_status, remaining = manager._get_locked_status(plate)
    if locked_status == "exit":
        return {
            "plate": plate,
            "status": "ignored",
            "time": now_str,
            "duration": None,
            "message": f"车辆处于出场锁定状态，还剩{remaining}秒"
        }

    # 强制出场（跳过最短停车时长检查）
    record_id, entry_time = active_record
    entry_dt = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
    duration = (datetime.now() - entry_dt).total_seconds() / 3600
    fee = calculate_fee(duration)
    VehicleDAO.update_exit(record_id, entry_time, fee)
    manager._set_locked_status(plate, "exit")
    manager._recently_exited[plate] = time.time()
    manager._entry_timestamps.pop(plate, None)

    fee_str = f"{fee:.0f}元" if fee > 0 else "免费"
    return {
        "plate": plate,
        "status": "exit",
        "time": now_str,
        "duration": round(duration, 2),
        "fee": fee,
        "message": f"手动出场成功，停车{duration:.2f}小时，费用：{fee_str}"
    }
