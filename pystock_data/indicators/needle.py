"""
DZS/DZT单针指标计算模块

功能：
- 计算DZS（3日单针）与DZT（21日单针）指标值
- 输入基础DataFrame，输出增强DataFrame

公式来源：pystock_data.indicators.tdx 公式函数库（HHV/LLV）

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import pandas as pd

from .base import IndicatorBase
from .tdx import HHV, LLV


class _NeedleBase(IndicatorBase):
    """单针指标基类：收盘价在N日高低区间的相对位置（百分位）"""

    required_fields = ['high', 'low', 'close']

    # 子类定义
    period = None      # 单针周期
    field_name = None  # 输出字段名

    def __init__(self):
        super().__init__(name=self.__class__.__name__.replace('Indicator', ''),
                         required_fields=self.required_fields)

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算单针指标

        Args:
            df (DataFrame): 基础数据，必须包含high、low、close字段

        Returns:
            DataFrame: 增强数据（基础字段 + 单针字段）
        """
        if not self.validate_input(df):
            return df.copy()

        df = df.copy()
        close, high, low = df['close'].values, df['high'].values, df['low'].values

        # 公式来源：tdx 公式函数库 HHV/LLV
        llv_low = LLV(low, self.period)
        hhv_close = HHV(close, self.period)
        needle = (close - llv_low) / (hhv_close - llv_low) * 100

        df[self.field_name] = pd.Series(needle, index=df.index).round(2)
        return df


class DZSIndicator(_NeedleBase):
    """
    DZS短线单针指标计算类

    功能：
        - 计算收盘价在3日高低区间的相对位置（短线超跌反弹观察）

    返回字段：
        dzs: 短线单针值（0~100百分位）
    """

    period = 3
    field_name = 'dzs'


class DZTIndicator(_NeedleBase):
    """
    DZT长线单针指标计算类

    功能：
        - 计算收盘价在21日高低区间的相对位置（中线位置观察）

    返回字段：
        dzt: 长线单针值（0~100百分位）
    """

    period = 21
    field_name = 'dzt'
