"""
ZX趋势组合指标计算模块

功能：
- 计算ZX短线趋势与ZX牛熊分界两个组合指标
- 输入基础DataFrame，输出增强DataFrame

公式来源：pystock_data.indicators.tdx 公式函数库（EMA/MA）

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import pandas as pd

from .base import IndicatorBase
from .tdx import EMA, MA as tdx_MA


class ZXShortTermTrendIndicator(IndicatorBase):
    """
    ZX短线趋势指标计算类

    功能：
        - 双层EMA平滑捕捉短线趋势方向
        - 输入基础DataFrame，输出增强DataFrame

    使用示例：
        >>> zx = ZXShortTermTrendIndicator()
        >>> zx_df = zx.calculate(basic_df)

    参数说明：
        n: EMA周期，默认10

    返回字段：
        zx_short_term_trend: 短线趋势值

    注意：
        - 输入DataFrame必须包含close字段
    """

    def __init__(self, n: int = 10):
        super().__init__(name='ZXShortTermTrend', required_fields=['close'])
        self.n = n

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算ZX短线趋势指标

        Args:
            df (DataFrame): 基础数据，必须包含close字段

        Returns:
            DataFrame: 增强数据（基础字段 + zx_short_term_trend）
        """
        if not self.validate_input(df):
            return df.copy()

        df = df.copy()
        close = df['close'].values

        # 公式来源：tdx 公式函数库 EMA（EMA套EMA双层平滑）
        trend = EMA(EMA(close, self.n), self.n)
        df['zx_short_term_trend'] = pd.Series(trend, index=df.index).round(2)

        return df


class ZXBullBearLineIndicator(IndicatorBase):
    """
    ZX牛熊分界指标计算类

    功能：
        - 四条不同周期均线的均值，作为牛熊分界参考线
        - 输入基础DataFrame，输出增强DataFrame

    使用示例：
        >>> zx = ZXBullBearLineIndicator()
        >>> zx_df = zx.calculate(basic_df)

    参数说明：
        m1/m2/m3/m4: 均线周期，默认14/28/57/114

    返回字段：
        zx_bull_bear_line: 牛熊分界线值

    注意：
        - 输入DataFrame必须包含close字段
    """

    def __init__(self, m1: int = 14, m2: int = 28, m3: int = 57, m4: int = 114):
        super().__init__(name='ZXBullBearLine', required_fields=['close'])
        self.m1 = m1
        self.m2 = m2
        self.m3 = m3
        self.m4 = m4

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算ZX牛熊分界指标

        Args:
            df (DataFrame): 基础数据，必须包含close字段

        Returns:
            DataFrame: 增强数据（基础字段 + zx_bull_bear_line）
        """
        if not self.validate_input(df):
            return df.copy()

        df = df.copy()
        close = df['close'].values

        # 公式来源：tdx 公式函数库 MA（四均线均值）
        bull_bear = (tdx_MA(close, self.m1) + tdx_MA(close, self.m2)
                     + tdx_MA(close, self.m3) + tdx_MA(close, self.m4)) / 4
        df['zx_bull_bear_line'] = pd.Series(bull_bear, index=df.index).round(2)

        return df
