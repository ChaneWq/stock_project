"""
DorisDB 数据写入模块（仅插入，不建表）

功能：
- 将特征 DataFrame 批量写入 DorisDB 目标表
- 目标表需已存在（PRIMARY KEY (code, trade_date)），本模块不做任何 DDL
- NaN 统一转 NULL

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import threading

import pandas as pd
from sqlalchemy import create_engine


class DorisWriter:
    """
    DorisDB 写入器

    使用示例：
        >>> writer = DorisWriter(CONFIG['db'], CONFIG['import']['table_name'])
        >>> writer.write(features_df)
    """

    def __init__(self, db_config: dict, table_name: str):
        """
        Args:
            db_config (dict): 数据库配置（host/port/user/password/database）
            table_name (str): 目标表名，需已存在
        """
        self.db_config = db_config
        self.table_name = table_name
        self._engine = None
        self._lock = threading.Lock()

    def _get_engine(self):
        """惰性创建 engine（线程安全单例）"""
        if self._engine is None:
            with self._lock:
                if self._engine is None:
                    cfg = self.db_config
                    url = (
                        f"mysql+pymysql://{cfg['user']}:{cfg['password']}"
                        f"@{cfg['host']}:{cfg['port']}/{cfg['database']}?charset=utf8mb4"
                    )
                    self._engine = create_engine(url)
        return self._engine

    def write(self, df: pd.DataFrame, chunksize: int = 1000) -> int:
        """
        批量插入数据（append 模式）

        Args:
            df (DataFrame): 待写入数据
            chunksize (int, optional): 单批行数，默认1000

        Returns:
            int: 写入行数

        Raises:
            Exception: 数据库连接或写入失败
        """
        if df is None or df.empty:
            return 0

        # NaN 转 None（SQL NULL）
        data = df.where(pd.notnull(df), None)

        data.to_sql(
            self.table_name,
            self._get_engine(),
            if_exists='append',
            index=False,
            chunksize=chunksize,
        )
        return len(data)

    def query_codes(self, sql: str) -> list:
        """
        执行查询并返回首列结果列表

        Args:
            sql (str): 查询语句（如股票清单）

        Returns:
            list: 首列值列表
        """
        with self._get_engine().connect() as conn:
            result = pd.read_sql(sql, conn)
        return result.iloc[:, 0].tolist() if not result.empty else []
