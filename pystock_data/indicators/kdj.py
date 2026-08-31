"""
KDJ指标计算模块

功能：
- 计算K、D、J三个指标值
- 输入基础DataFrame，输出增强DataFrame
- 使用标准算法计算KDJ

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pandas as pd
import numpy as np
from .base import IndicatorBase
from .tdx import HHV, LLV, SMA


class KDJIndicator(IndicatorBase):
    """
    KDJ指标计算类
    
    功能：
        - 计算K、D、J三个指标值
        - 输入基础DataFrame，输出增强DataFrame
    
    使用示例：
        >>> kdj = KDJIndicator()
        >>> kdj_df = kdj.calculate(basic_df)
    
    参数说明：
        n: 周期参数，默认9
        m1: K值平滑周期，默认3
        m2: D值平滑周期，默认3
    
    返回字段：
        kdj_k: K值
        kdj_d: D值
        kdj_j: J值
    
    注意：
        - 输入DataFrame必须包含high、low、close字段
        - KDJ指标用于判断超买超卖状态
    """
    
    def __init__(self, n: int = 9, m1: int = 3, m2: int = 3):
        """
        初始化KDJ指标
        
        Args:
            n (int, optional): 周期参数，默认为9
            m1 (int, optional): K值平滑周期，默认为3
            m2 (int, optional): D值平滑周期，默认为3
        """
        super().__init__(name='KDJ', required_fields=['high', 'low', 'close'])
        self.n = n
        self.m1 = m1
        self.m2 = m2
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算KDJ指标
        
        Args:
            df (DataFrame): 基础数据，必须包含high、low、close字段
        
        Returns:
            DataFrame: 增强数据（基础字段 + kdj_k, kdj_d, kdj_j）
        
        Raises:
            ValueError: 如果输入DataFrame缺少必需字段
        
        Example:
            >>> kdj = KDJIndicator()
            >>> kdj_df = kdj.calculate(basic_df, n=9)
        """
        # 验证输入
        if not self.validate_input(df):
            return df.copy()
        
        # 复制DataFrame避免修改原数据
        df = df.copy()
        
        # 计算RSV（未成熟随机值）
        # 公式来源：tdx 公式函数库 LLV/HHV（标准滚动极值，前 N-1 行为 NaN）
        low_n = pd.Series(LLV(df['low'].values, self.n), index=df.index)
        high_n = pd.Series(HHV(df['high'].values, self.n), index=df.index)
        # 前 n-1 行用部分窗口极值补齐（保持历史行为：min_periods=1）
        low_n = low_n.fillna(df['low'].expanding().min())
        high_n = high_n.fillna(df['high'].expanding().max())
        
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        
        # 处理除零异常
        rsv = rsv.fillna(50)
        
        # 计算K值（RSV的m1周期平滑）
        # 公式来源：tdx 公式函数库 SMA(X,M,1)，等价于 ewm(com=M-1)
        k = SMA(rsv.values, self.m1, 1)
        df['kdj_k'] = pd.Series(k, index=df.index)
        
        # 计算D值（K值的m2周期平滑）
        d = SMA(k, self.m2, 1)
        df['kdj_d'] = pd.Series(d, index=df.index)
        
        # 计算J值（3K - 2D）
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
        
        # 保留两位小数
        df['kdj_k'] = df['kdj_k'].round(2)
        df['kdj_d'] = df['kdj_d'].round(2)
        df['kdj_j'] = df['kdj_j'].round(2)
        
        return df