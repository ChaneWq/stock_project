"""
ZXT砖型图指标计算模块

功能：
- 计算ZXT（砖型图）指标值
- 输入基础DataFrame，输出增强DataFrame

公式来源：pystock_data.indicators.tdx 公式函数库（HHV/LLV/SMA）

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import numpy as np
import pandas as pd

from .base import IndicatorBase
from .tdx import HHV, LLV, SMA


class ZXTIndicator(IndicatorBase):
    """
    ZXT砖型图指标计算类

    功能：
        - 基于价格在近期高低区间的位置，经SMA平滑后构造砖型强度
        - 输入基础DataFrame，输出增强DataFrame

    使用示例：
        >>> zxt = ZXTIndicator()
        >>> zxt_df = zxt.calculate(basic_df)

    参数说明：
        n: 高低区间周期，默认4
        m1/m2: 平滑周期，默认4/6

    返回字段：
        zxt: 砖型图强度值（强度>4时取超出部分，否则为0）

    注意：
        - 输入DataFrame必须包含high、low、close字段
    """

    def __init__(self, n: int = 4, m1: int = 4, m2: int = 6):
        super().__init__(name='ZXT', required_fields=['high', 'low', 'close'])
        self.n = n
        self.m1 = m1
        self.m2 = m2

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算ZXT指标

        Args:
            df (DataFrame): 基础数据，必须包含high、low、close字段

        Returns:
            DataFrame: 增强数据（基础字段 + zxt）
        """
        if not self.validate_input(df):
            return df.copy()

        df = df.copy()
        close, high, low = df['close'].values, df['high'].values, df['low'].values

        # 公式来源：tdx 公式函数库 HHV/LLV/SMA
        hhv_high = HHV(high, self.n)
        llv_low = LLV(low, self.n)

        var1 = (hhv_high - close) / (hhv_high - llv_low) * 100 - 90
        var2 = SMA(var1, self.m1, 1) + 100
        var3 = (close - llv_low) / (hhv_high - llv_low) * 100
        var4 = SMA(var3, self.m2, 1)
        var5 = SMA(var4, self.m2, 1) + 100
        var6 = var5 - var2

        zxt = np.where(var6 > 4, var6 - 4, 0.0)
        df['zxt'] = pd.Series(zxt, index=df.index).round(2)

        return df
