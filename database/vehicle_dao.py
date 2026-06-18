"""
车辆数据访问对象 (DAO)
封装所有数据库操作
"""
from datetime import datetime
from database.db import get_db


class VehicleDAO:
    """
    车辆记录数据访问对象
    """
    
    @staticmethod
    def find_active_vehicle(plate: str):
        """
        查询在场车辆记录
        
        :param plate: 车牌号
        :return: tuple (id, entry_time) 或 None
        """
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, entry_time FROM vehicle_record
            WHERE plate_number = ? AND status = 0
            ORDER BY entry_time DESC
            LIMIT 1
        ''', (plate,))
        
        result = cursor.fetchone()
        conn.close()
        return result
    
    @staticmethod
    def insert_entry(plate: str) -> int:
        """
        插入入场记录
        
        :param plate: 车牌号
        :return: 新记录ID
        """
        conn = get_db()
        cursor = conn.cursor()
        
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO vehicle_record (plate_number, entry_time, status)
            VALUES (?, ?, 0)
        ''', (plate, now))
        
        record_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return record_id
    
    @staticmethod
    def update_exit(record_id: int, entry_time: str, fee: float = 0.0):
        """
        更新出场记录

        :param record_id: 记录ID
        :param entry_time: 入场时间字符串
        :param fee: 停车费用
        :return: (停车时长小时, 费用)
        """
        conn = get_db()
        cursor = conn.cursor()

        now = datetime.now()
        exit_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

        # 计算停车时长
        entry = datetime.strptime(entry_time, "%Y-%m-%d %H:%M:%S")
        duration = (now - entry).total_seconds() / 3600  # 转换为小时

        cursor.execute('''
            UPDATE vehicle_record
            SET exit_time = ?, duration = ?, fee = ?, status = 1
            WHERE id = ?
        ''', (exit_time_str, duration, fee, record_id))

        conn.commit()
        conn.close()
        return duration, fee
    
    @staticmethod
    def get_active_vehicles():
        """
        获取所有在场车辆
        
        :return: List[dict]
        """
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT plate_number, entry_time 
            FROM vehicle_record
            WHERE status = 0
            ORDER BY entry_time DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        return [{"plate": row["plate_number"], "entry_time": row["entry_time"]} 
                for row in rows]
    
    @staticmethod
    def get_history(limit=100):
        """
        获取历史记录
        
        :param limit: 返回条数
        :return: List[dict]
        """
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM vehicle_record
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]