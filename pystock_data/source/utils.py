"""
数据源工具模块

功能：
- 标准化数据字段命名
- 数据格式转换
- 日期处理工具

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pandas as pd
from datetime import datetime


def standardize_fields(df: pd.DataFrame, stock_code: str = None) -> pd.DataFrame:
    """
    标准化DataFrame字段命名
    
    Args:
        df (DataFrame): 原始DataFrame
        stock_code (str, optional): 股票代码，添加到DataFrame中
    
    Returns:
        DataFrame: 标准化后的DataFrame
    
    Example:
        >>> df = standardize_fields(raw_df, '000400')
        >>> # 字段：stock_code, datetime, trade_date, open, close, high, low, volume, amount
    """
    # 复制DataFrame避免修改原数据
    df = df.copy()
    
    # 处理datetime既是索引名又是列名的情况
    # 如果索引名是datetime
    if df.index.name == 'datetime':
        # 先检查datetime列是否已存在
        if 'datetime' in df.columns:
            # 删除列中的datetime（保留索引中的datetime）
            df = df.drop(columns=['datetime'])
        # 然后reset_index，将datetime索引转为datetime列
        df = df.reset_index()
    
    # 字段映射：原始字段名 → 标准字段名
    field_mapping = {
        'open': 'open',
        'close': 'close',
        'high': 'high',
        'low': 'low',
        'vol': 'volume',      # 统一用volume
        'amount': 'amount'
    }
    
    # 重命名字段
    df = df.rename(columns=field_mapping)
    
    # 处理分时数据的price字段（分时数据只有price字段）
    if 'price' in df.columns and 'close' not in df.columns:
        # 分时数据：price作为close（收盘价）
        df['close'] = df['price']
        df['open'] = df['price']
        df['high'] = df['price']
        df['low'] = df['price']
    
    # 确保datetime字段存在且类型正确
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'])
    
    # 添加交易日期字段（YYYY-MM-DD格式）
    if 'datetime' in df.columns:
        df['trade_date'] = df['datetime'].dt.strftime('%Y-%m-%d')
    
    # 添加股票代码字段
    if stock_code:
        df['stock_code'] = stock_code
    
    # 标准字段顺序
    standard_columns = ['stock_code', 'datetime', 'trade_date', 
                        'open', 'close', 'high', 'low', 'volume', 'amount']
    
    # 只保留存在的字段
    existing_columns = [col for col in standard_columns if col in df.columns]
    
    return df[existing_columns]


def add_minute_fields(df: pd.DataFrame, stock_code: str = None, date: str = None) -> pd.DataFrame:
    """
    为分时数据添加hour和minute字段
    
    Args:
        df (DataFrame): 分时DataFrame
        stock_code (str, optional): 股票代码
        date (str, optional): 日期（格式YYYYMMDD），用于生成datetime
    
    Returns:
        DataFrame: 包含hour和minute字段的DataFrame
    
    Example:
        >>> minute_df = add_minute_fields(raw_df, '000400', '20260624')
        >>> # 字段包含：datetime, hour, minute
    
    注意：
        - 分时数据共240分钟（从9:30到14:59）
        - 上午：9:30-11:30（120分钟）
        - 下午：13:00-14:59（120分钟）
    """
    # 复制DataFrame避免修改原数据
    df = df.copy()
    
    # 分时数据没有datetime字段，需要生成
    if 'datetime' not in df.columns:
        # 获取数据长度（应该为240）
        n = len(df)
        
        # 生成时间序列（从9:30到14:59）
        # 上午：9:30-11:30（前120分钟）
        # 下午：13:00-14:59（后120分钟）
        
        # 上午时段（9:30-11:30）
        morning_times = []
        for i in range(120):
            hour = 9 + (i // 60)
            minute = 30 + (i % 60)
            if minute >= 60:
                hour += 1
                minute -= 60
            morning_times.append(f"{hour:02d}:{minute:02d}")
        
        # 下午时段（13:00-14:59）
        afternoon_times = []
        for i in range(120):
            hour = 13 + (i // 60)
            minute = i % 60
            afternoon_times.append(f"{hour:02d}:{minute:02d}")
        
        # 合成时间列表
        time_list = morning_times + afternoon_times
        
        # 生成datetime字段
        if date:
            # 使用传入的日期
            date_str = pd.to_datetime(date, format='%Y%m%d').strftime('%Y-%m-%d')
            df['datetime'] = pd.to_datetime([date_str + ' ' + t for t in time_list[:n]])
        else:
            # 使用当前日期
            today = datetime.now().strftime('%Y-%m-%d')
            df['datetime'] = pd.to_datetime([today + ' ' + t for t in time_list[:n]])
    
    # 标准化基础字段
    df = standardize_fields(df, stock_code)
    
    # 添加hour和minute字段
    if 'datetime' in df.columns:
        df['hour'] = df['datetime'].dt.hour
        df['minute'] = df['datetime'].dt.minute
    
    return df


def validate_bar_data(df: pd.DataFrame) -> bool:
    """
    验证K线数据完整性
    
    Args:
        df (DataFrame): K线DataFrame
    
    Returns:
        bool: 数据是否完整
    
    Example:
        >>> is_valid = validate_bar_data(df)
    """
    # K线数据必需字段
    required_fields = ['datetime', 'open', 'close', 'high', 'low', 'volume']
    
    return all(field in df.columns for field in required_fields)


def validate_minute_data(df: pd.DataFrame) -> bool:
    """
    验证分时数据完整性
    
    Args:
        df (DataFrame): 分时DataFrame
    
    Returns:
        bool: 数据是否完整
    
    Example:
        >>> is_valid = validate_minute_data(df)
    """
    # 分时数据必需字段（包含hour和minute）
    required_fields = ['datetime', 'open', 'close', 'high', 'low', 'volume', 'hour', 'minute']
    
    return all(field in df.columns for field in required_fields)