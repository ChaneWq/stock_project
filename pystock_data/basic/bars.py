"""
基础K线数据模块

功能：
- 提供日线、周线、月线数据获取功能
- 标准化数据字段命名和格式
- 提供统一的数据访问接口

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pandas as pd
from ..source.tdx_source import TdxSource


class BasicBars:
    """
    基础K线数据类
    
    功能：
        - 获取日线数据
        - 获取周线数据
        - 获取月线数据
        - 返回标准DataFrame
    
    使用示例：
        >>> bars = BasicBars()
        >>> day_df = bars.get_daily('000400', 100)
        >>> week_df = bars.get_weekly('000400', 50)
        >>> month_df = bars.get_monthly('000400', 30)
    
    返回字段：
        stock_code: 股票代码
        datetime: 时间戳
        trade_date: 交易日期（YYYY-MM-DD）
        open: 开盘价
        close: 收盘价
        high: 最高价
        low: 最低价
        volume: 成交量
        amount: 成交额
    """
    
    def __init__(self, market: str = 'std', thread_safe: bool = False):
        """
        初始化基础K线数据类

        Args:
            market (str): 通达信市场参数，默认为'std'
            thread_safe (bool): 是否使用线程独立 client，默认 False
                多线程并发采集时设为 True，每个线程拥有独立 client
        """
        self.source = TdxSource(market=market, thread_safe=thread_safe)
    
    def get_daily(self, code: str, n: int = 400) -> pd.DataFrame:
        """
        获取日线数据
        
        Args:
            code (str): 股票代码（6位字符串）
            n (int, optional): 获取的数据数量，默认为400
        
        Returns:
            DataFrame: 日线数据（标准字段）
        
        Example:
            >>> bars = BasicBars()
            >>> day_df = bars.get_daily('000400', 400)
            >>> print(day_df.columns)
            >>> # ['stock_code', 'datetime', 'trade_date', 'open', 'close', 'high', 'low', 'volume', 'amount']
        
        注意：
            - 最新数据在第一行（index=0）
            - 数据按时间倒序排列
        """
        # freq=9 表示日线
        df = self.source.fetch_bars(code, freq=9, offset=n)
        
        # 数据排序：最新数据在第一行
        if not df.empty:
            df = df.sort_values('datetime', ascending=False).reset_index(drop=True)
        
        return df
    
    def get_weekly(self, code: str, n: int = 100) -> pd.DataFrame:
        """
        获取周线数据
        
        Args:
            code (str): 股票代码（6位字符串）
            n (int, optional): 获取的数据数量，默认为100
        
        Returns:
            DataFrame: 周线数据（标准字段）
        
        Example:
            >>> bars = BasicBars()
            >>> week_df = bars.get_weekly('000400', 50)
        """
        # freq=5 表示周线
        df = self.source.fetch_bars(code, freq=5, offset=n)
        
        # 数据排序：最新数据在第一行
        if not df.empty:
            df = df.sort_values('datetime', ascending=False).reset_index(drop=True)
        
        return df
    
    def get_monthly(self, code: str, n: int = 100) -> pd.DataFrame:
        """
        获取月线数据
        
        Args:
            code (str): 股票代码（6位字符串）
            n (int, optional): 获取的数据数量，默认为100
        
        Returns:
            DataFrame: 月线数据（标准字段）
        
        Example:
            >>> bars = BasicBars()
            >>> month_df = bars.get_monthly('000400', 30)
        """
        # freq=6 表示月线
        df = self.source.fetch_bars(code, freq=6, offset=n)
        
        # 数据排序：最新数据在第一行
        if not df.empty:
            df = df.sort_values('datetime', ascending=False).reset_index(drop=True)
        
        return df
    
    def get_latest(self, code: str) -> pd.DataFrame:
        """
        获取最新一根K线（日线）
        
        Args:
            code (str): 股票代码
        
        Returns:
            DataFrame: 最新K线数据（单行DataFrame）
        
        Example:
            >>> bars = BasicBars()
            >>> latest_df = bars.get_latest('000400')
        """
        df = self.get_daily(code, n=1)
        return df