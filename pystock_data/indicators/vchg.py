"""
量涨跌幅指标计算模块

功能：
- 计算成交量环比涨跌幅（当前量相对昨日量的百分比变化）
- 公式：(当前量 − 昨日量) ÷ 昨日量 × 100
- 输入基础DataFrame，输出增强DataFrame

作者：PyStock项目组
日期：2026-09-27
版本：1.0.0
"""

import pandas as pd
from .base import IndicatorBase


class VolumeChangeRateIndicator(IndicatorBase):
    """
    量涨跌幅指标计算类

    功能：
        - 计算成交量环比涨跌幅（正数放量、负数缩量，单位：%）
        - 输入基础DataFrame，输出增强DataFrame

    使用示例：
        >>> vchg = VolumeChangeRateIndicator()
        >>> vchg_df = vchg.calculate(basic_df)

    参数说明：
        无额外参数（公式只涉及昨日量，无周期概念）

    返回字段：
        vchg: 量涨跌幅（%），保留两位小数

    注意：
        - 输入DataFrame必须包含volume字段，且按时间正序（最新在最后一行）
        - 第一行无昨日数据，输出NaN
        - 昨日量为0（停牌后复牌/新股等）时除零无意义，输出NaN
    """

    def __init__(self):
        super().__init__(name='VCHG', required_fields=['volume'])

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算量涨跌幅指标

        Args:
            df (DataFrame): 基础数据，必须包含volume字段（时间正序）

        Returns:
            DataFrame: 增强数据（基础字段 + vchg）

        Example:
            >>> vchg = VolumeChangeRateIndicator()
            >>> df = vchg.calculate(basic_df)  # 输出基础字段 + vchg
        """
        # 验证输入DataFrame
        if not self.validate_input(df):
            return df.copy()

        df = df.copy()

        # 昨日量（第一行为NaN）
        prev_volume = df['volume'].shift(1)

        # (当前量 − 昨日量) ÷ 昨日量 × 100
        # 昨日量为0或NaN时结果自然为NaN（除零产生inf，统一转为NaN）
        vchg = (df['volume'] - prev_volume) / prev_volume * 100
        vchg = vchg.replace([float('inf'), float('-inf')], float('nan'))

        # 保留两位小数
        df['vchg'] = vchg.round(2)

        return df
