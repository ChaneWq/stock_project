"""
SQLite 连接管理

设计：
- 每次 get_conn() 返回独立短连接（用完即关），天然线程安全
- WAL 模式：写入不阻塞并发读取（单写多读）
- 写操作统一经 write_conn() 串行锁，避免 "database is locked"
"""

import os
import sqlite3
import threading
from contextlib import contextmanager

from .config import DB_PATH

# 进程内写锁（SQLite 同一时刻只允许一个写者）
_write_lock = threading.Lock()


def _ensure_schema(conn: sqlite3.Connection):
    """建库建表（幂等，schema.sql 全部 IF NOT EXISTS）"""
    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema.sql')
    with open(schema_path, encoding='utf-8') as f:
        conn.executescript(f.read())


def get_conn() -> sqlite3.Connection:
    """
    获取短连接（自动建库建表）

    使用方式：调用方自管关闭，如
        >>> conn = get_conn()
        >>> try:
        ...     rows = conn.execute(sql, params).fetchall()
        >>> finally:
        ...     conn.close()
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")     # 写不阻塞读
    conn.execute("PRAGMA synchronous=NORMAL")   # 安全且更快的落盘档位
    _ensure_schema(conn)
    return conn


@contextmanager
def write_conn():
    """
    获取写入连接（带锁、事务提交）

    Example:
        >>> with write_conn() as conn:
        ...     conn.executemany(sql, rows)
    """
    with _write_lock:
        conn = get_conn()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
