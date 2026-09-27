"""
MA斜率指标计算模块

功能：
- 计算均线环比涨跌幅（今日MA相对k日前MA的百分比变化）
- 公式：(今日MA − k日前MA) ÷ k日前MA × 100
- 输入基础DataFrame，输出增强DataFrame

作者：PyStock项目组
日期：2026-09-27
版本：1.0.0
"""

import pandas as pd
from .base import IndicatorBase
from .tdx import MA as tdx_MA


class MASlopeIndicator(IndicatorBase):
    """
    MA斜率指标计算类

    功能：
        - 计算均线斜率（正数均线上行、负数下行，单位：%）
        - k=1 即与上一交易日对比（斜率1）
        - 输入基础DataFrame，输出增强DataFrame

    使用示例：
        >>> maslope = MASlopeIndicator()
        >>> maslope_df = maslope.calculate(basic_df)  # 输出 ma7_slope1

        # 一次计算多个偏移
        >>> maslope_df = maslope.calculate(basic_df, ks=[1, 2, 3])
        # 输出 ma7_slope1 / ma7_slope2 / ma7_slope3

    参数说明：
        n: MA周期，默认7
        ks: 对比偏移列表（与k个交易日前对比），默认[1]

    返回字段：
        ma{n}_slope{k}: MA斜率（%），保留两位小数，默认 ma7_slope1

    注意：
        - 输入DataFrame必须包含close字段，且按时间正序（最新在最后一行）
        - MA计算与MAIndicator行为一致：前n-1行用部分窗口均值补齐
        - 前k行无对比基准，输出NaN
        - 对比基准MA为0时除零无意义，输出NaN
    """

    def __init__(self, n: int = 7, ks=None):
        """
        初始化MA斜率指标

        Args:
            n (int, optional): MA周期，默认7
            ks (List[int], optional): 对比偏移列表，默认[1]
        """
        if not isinstance(n, int) or n <= 0:
            raise ValueError(f"n必须为正整数，当前值: {n}")
        ks = ks or [1]
        self._validate_periods(ks)
        super().__init__(name=f'MA{n}Slope', required_fields=['close'])
        self.n = n
        self.ks = list(ks)

    def calculate(self, df: pd.DataFrame, ks=None) -> pd.DataFrame:
        """
        计算MA斜率指标

        Args:
            df (DataFrame): 基础数据，必须包含close字段（时间正序）
            ks (List[int], optional): 对比偏移列表
                None - 使用初始化时设置的ks（默认[1]）
                List[int] - 使用运行时传入的自定义偏移列表

        Returns:
            DataFrame: 增强数据（基础字段 + ma{n}_slope{k}字段）

        Raises:
            ValueError: 如果ks参数不合法

        Example:
            # 使用默认偏移
            >>> maslope = MASlopeIndicator()
            >>> df = maslope.calculate(basic_df)  # 输出ma7_slope1

            # 运行时动态指定偏移
            >>> df = maslope.calculate(basic_df, ks=[1, 2, 3])

        Note:
            - ks参数支持运行时动态传入，无需重新创建实例
            - MA中间值不取整，仅最终斜率保留两位小数
        """
        # 验证输入DataFrame
        if not self.validate_input(df):
            return df.copy()

        # 确定使用的偏移参数
        use_ks = ks if ks is not None else self.ks

        # 验证偏移参数
        self._validate_periods(use_ks)

        # 复制DataFrame避免修改原数据
        df = df.copy()

        # MA计算（公式来源：tdx 公式函数库 MA，前n-1行用部分窗口均值补齐，与MAIndicator一致）
        ma = pd.Series(tdx_MA(df['close'].values, self.n), index=df.index)
        ma = ma.fillna(df['close'].expanding().mean())

        # 计算各偏移的斜率：(今日MA − k日前MA) ÷ k日前MA × 100
        for k in use_ks:
            prev_ma = ma.shift(k)
            slope = (ma - prev_ma) / prev_ma * 100
            # 基准MA为0时除零产生inf，统一转为NaN
            slope = slope.replace([float('inf'), float('-inf')], float('nan'))
            # 字段名：ma7_slope1等，保留两位小数
            df[f'ma{self.n}_slope{k}'] = slope.round(2)

        return df

    def get_ks(self) -> list:
        """
        获取对比偏移列表

        Returns:
            List[int]: 对比偏移列表
        """
        return self.ks
