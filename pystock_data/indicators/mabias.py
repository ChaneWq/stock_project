"""
MA偏离度（乖离率）指标计算模块

功能：
- 计算收盘价相对均线的偏离度（乖离率BIAS）
- 公式：(收盘价 − MA_n) ÷ MA_n × 100
- 输入基础DataFrame，输出增强DataFrame

作者：PyStock项目组
日期：2026-09-27
版本：1.0.0
"""

import pandas as pd
from typing import List
from .base import IndicatorBase
from .tdx import MA as tdx_MA


class MABiasIndicator(IndicatorBase):
    """
    MA偏离度（乖离率）指标计算类

    功能：
        - 计算收盘价相对MA的偏离百分比（正值超买倾向、负值超卖倾向，单位：%）
        - 即经典乖离率指标BIAS
        - 输入基础DataFrame，输出增强DataFrame

    使用示例：
        >>> mabias = MABiasIndicator()
        >>> mabias_df = mabias.calculate(basic_df)  # 输出 bias7

        # 一次计算多个周期
        >>> mabias_df = mabias.calculate(basic_df, periods=[7, 20])
        # 输出 bias7 / bias20

    参数说明：
        periods: MA周期列表，默认[7]

    返回字段：
        bias{n}: n日乖离率（%），保留两位小数，默认 bias7

    注意：
        - 输入DataFrame必须包含close字段
        - MA计算与MAIndicator行为一致：前n-1行用部分窗口均值补齐
        - MA为0时除零无意义，输出NaN
    """

    def __init__(self, periods: List[int] = None):
        """
        初始化MA偏离度指标

        Args:
            periods (List[int], optional): MA周期列表，默认为[7]
        """
        super().__init__(name='MABias', required_fields=['close'])
        self.periods = periods or [7]

    def calculate(self, df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """
        计算MA偏离度指标

        Args:
            df (DataFrame): 基础数据，必须包含close字段
            periods (List[int], optional): MA周期列表
                None - 使用初始化时设置的periods（默认[7]）
                List[int] - 使用运行时传入的自定义周期列表

        Returns:
            DataFrame: 增强数据（基础字段 + bias字段）

        Raises:
            ValueError: 如果periods参数不合法

        Example:
            # 使用默认周期
            >>> mabias = MABiasIndicator()
            >>> df = mabias.calculate(basic_df)  # 输出bias7

            # 运行时动态指定周期
            >>> df = mabias.calculate(basic_df, periods=[7, 20])  # 输出bias7、bias20

        Note:
            - periods参数支持运行时动态传入，无需重新创建实例
            - MA中间值不取整，仅最终偏离度保留两位小数
        """
        # 验证输入DataFrame
        if not self.validate_input(df):
            return df.copy()

        # 确定使用的周期参数
        use_periods = periods if periods is not None else self.periods

        # 验证周期参数
        self._validate_periods(use_periods)

        # 复制DataFrame避免修改原数据
        df = df.copy()

        # 计算各周期乖离率：(收盘价 − MA_n) ÷ MA_n × 100
        for period in use_periods:
            # 公式来源：tdx 公式函数库 MA，前n-1行用部分窗口均值补齐（与MAIndicator一致）
            ma = pd.Series(tdx_MA(df['close'].values, period), index=df.index)
            ma = ma.fillna(df['close'].expanding().mean())

            # MA为0时除零产生inf，统一转为NaN
            bias = (df['close'] - ma) / ma * 100
            bias = bias.replace([float('inf'), float('-inf')], float('nan'))

            # 字段名：bias7、bias20等，保留两位小数
            df[f'bias{period}'] = bias.round(2)

        return df

    def get_periods(self) -> List[int]:
        """
        获取MA周期列表

        Returns:
            List[int]: MA周期列表
        """
        return self.periods
