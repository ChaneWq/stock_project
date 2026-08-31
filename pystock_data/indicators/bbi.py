"""
BBI多空均线指标计算模块

功能：
- 计算BBI（多空均线）指标值
- 输出基础DataFrame，输出增强DataFrame

公式来源：pystock_data.indicators.tdx 公式函数库（BBI）

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import pandas as pd

from .base import IndicatorBase
from .tdx import MA as tdx_MA


class BBIIndicator(IndicatorBase):
    """
    BBI多空均线指标计算类

    功能：
        - 计算 BBI = (MA3 + MA6 + MA12 + MA24) / 4
        - 输入基础DataFrame，输出增强DataFrame

    使用示例：
        >>> bbi = BBIIndicator()
        >>> bbi_df = bbi.calculate(basic_df)

    参数说明：
        m1/m2/m3/m4: 均线周期，默认3/6/12/24

    返回字段：
        bbi: 多空均线值

    注意：
        - 输入DataFrame必须包含close字段
        - 前 max(m4)-1 行为NaN（标准tdx行为，不补值）
    """

    def __init__(self, m1: int = 3, m2: int = 6, m3: int = 12, m4: int = 24):
        super().__init__(name='BBI', required_fields=['close'])
        self.m1 = m1
        self.m2 = m2
        self.m3 = m3
        self.m4 = m4

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算BBI指标

        Args:
            df (DataFrame): 基础数据，必须包含close字段

        Returns:
            DataFrame: 增强数据（基础字段 + bbi）
        """
        if not self.validate_input(df):
            return df.copy()

        df = df.copy()
        close = df['close'].values

        # 公式来源：tdx 公式函数库 BBI
        bbi = (tdx_MA(close, self.m1) + tdx_MA(close, self.m2)
               + tdx_MA(close, self.m3) + tdx_MA(close, self.m4)) / 4
        df['bbi'] = pd.Series(bbi, index=df.index).round(2)

        return df
