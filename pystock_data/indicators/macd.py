"""
MACD指标计算模块

功能：
- 计算DIF、DEA、MACD三个指标值
- 输入基础DataFrame，输出增强DataFrame
- 使用标准算法计算MACD

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pandas as pd
import numpy as np
from .base import IndicatorBase


class MACDIndicator(IndicatorBase):
    """
    MACD指标计算类
    
    功能：
        - 计算DIF、DEA、MACD三个指标值
        - 输入基础DataFrame，输出增强DataFrame
    
    使用示例：
        >>> macd = MACDIndicator()
        >>> macd_df = macd.calculate(basic_df)
    
    参数说明：
        fast_period: 快速EMA周期，默认12
        slow_period: 慢速EMA周期，默认26
        signal_period: DEA周期，默认9
    
    返回字段：
        macd_dif: DIF线（快线）
        macd_dea: DEA线（慢线）
        macd_macd: MACD柱
    
    注意：
        - 输入DataFrame必须包含close字段
        - MACD指标用于判断趋势方向
    """
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        """
        初始化MACD指标
        
        Args:
            fast_period (int, optional): 快速EMA周期，默认为12
            slow_period (int, optional): 慢速EMA周期，默认为26
            signal_period (int, optional): DEA周期，默认为9
        """
        super().__init__(name='MACD', required_fields=['close'])
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算MACD指标
        
        Args:
            df (DataFrame): 基础数据，必须包含close字段
        
        Returns:
            DataFrame: 增强数据（基础字段 + macd_dif, macd_dea, macd_macd）
        
        Raises:
            ValueError: 如果输入DataFrame缺少必需字段
        
        Example:
            >>> macd = MACDIndicator()
            >>> macd_df = macd.calculate(basic_df)
        """
        # 验证输入
        if not self.validate_input(df):
            return df.copy()
        
        # 复制DataFrame避免修改原数据
        df = df.copy()
        
        # 计算快速EMA
        ema_fast = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        
        # 计算慢速EMA
        ema_slow = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        
        # 计算DIF（快线 - 慢线）
        df['macd_dif'] = ema_fast - ema_slow
        
        # 计算DEA（DIF的signal_period周期EMA）
        df['macd_dea'] = df['macd_dif'].ewm(span=self.signal_period, adjust=False).mean()
        
        # 计算MACD柱（2*(DIF - DEA)）
        df['macd_macd'] = 2 * (df['macd_dif'] - df['macd_dea'])
        
        # 保留两位小数
        df['macd_dif'] = df['macd_dif'].round(2)
        df['macd_dea'] = df['macd_dea'].round(2)
        df['macd_macd'] = df['macd_macd'].round(2)
        
        return df