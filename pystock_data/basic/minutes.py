"""
基础分时数据模块

功能：
- 提供分时数据获取功能
- 标准化数据字段命名和格式
- 提供统一的数据访问接口

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pandas as pd
from ..source.tdx_source import TdxSource


class BasicMinutes:
    """
    基础分时数据类
    
    功能：
        - 获取指定日期的分时数据
        - 返回包含hour和minute字段的标准DataFrame
        - 提供时间范围查询功能
    
    使用示例：
        >>> minutes = BasicMinutes()
        >>> minute_df = minutes.get_data('000400', '20260624')
    
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
        hour: 小时
        minute: 分钟
    """
    
    def __init__(self):
        """
        初始化基础分时数据类
        
        创建TdxSource数据源实例
        """
        self.source = TdxSource()
    
    def get_data(self, code: str, date: str) -> pd.DataFrame:
        """
        获取指定日期的分时数据
        
        Args:
            code (str): 股票代码（6位字符串）
            date (str): 日期（格式YYYYMMDD）
        
        Returns:
            DataFrame: 分时数据（包含hour和minute字段）
        
        Example:
            >>> minutes = BasicMinutes()
            >>> minute_df = minutes.get_data('000400', '20260624')
            >>> print(minute_df.columns)
            >>> # ['stock_code', 'datetime', 'trade_date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'hour', 'minute']
        
        注意：
            - 分时数据从9:30到14:59（240分钟）
            - 数据按时间正序排列（从早到晚）
        """
        df = self.source.fetch_minutes(code, date)
        
        # 数据排序：时间正序（从早到晚）
        if not df.empty:
            df = df.sort_values('datetime', ascending=True).reset_index(drop=True)
        
        return df
    
    def get_data_by_range(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        获取日期范围内的分时数据
        
        Args:
            code (str): 股票代码
            start_date (str): 开始日期（格式YYYYMMDD）
            end_date (str): 结束日期（格式YYYYMMDD）
        
        Returns:
            DataFrame: 合并的分时数据
        
        Example:
            >>> minutes = BasicMinutes()
            >>> df = minutes.get_data_by_range('000400', '20260620', '20260624')
        
        注意：
            - 日期范围功能需要循环获取每一天数据
            - 所有数据合并为一个大DataFrame
        """
        # TODO: 实现日期范围查询（可选扩展）
        # 需要循环获取每一天的分时数据并合并
        raise NotImplementedError("日期范围查询功能待实现")