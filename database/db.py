"""
数据库模块
SQLite数据库连接与管理
"""
import sqlite3
import os
from pathlib import Path

# 数据库文件路径
DB_PATH = Path(__file__).parent.parent / "data" / "parking.db"


def ensure_data_dir():
    """确保数据目录存在"""
    data_dir = DB_PATH.parent
    data_dir.mkdir(parents=True, exist_ok=True)


def get_db():
    """
    获取数据库连接
    
    :return: sqlite3.Connection
    """
    ensure_data_dir()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # 使查询结果可通过列名访问
    return conn


def init_db():
    """
    初始化数据库表结构
    创建 vehicle_record 表
    """
    ensure_data_dir()
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vehicle_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate_number TEXT NOT NULL,
            entry_time DATETIME NOT NULL,
            exit_time DATETIME,
            duration REAL,
            fee REAL DEFAULT 0,
            status INTEGER DEFAULT 0 CHECK(status IN (0, 1)),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 兼容旧表：如果 fee 列不存在则添加
    try:
        cursor.execute('ALTER TABLE vehicle_record ADD COLUMN fee REAL DEFAULT 0')
    except Exception:
        pass  # 列已存在，忽略
    
    # 创建索引优化查询
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_plate_status 
        ON vehicle_record(plate_number, status)
    ''')
    
    conn.commit()
    conn.close()
    print("[Database] 数据库初始化完成")