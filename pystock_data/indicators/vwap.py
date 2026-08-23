"""
分时均价线（VWAP）指标计算模块

功能：
- 计算当日分时均价线（股票软件分时图中的黄线）
- 均价(t) = 累计成交额 / 累计成交量
- 输入基础DataFrame，输出增强DataFrame

作者：PyStock项目组
日期：2026-08-24
版本：1.0.0
"""

import pandas as pd
from .base import IndicatorBase


class VWAPIndicator(IndicatorBase):
    """
    分时均价线指标计算类

    功能：
        - 计算当日累计均价（VWAP，Volume Weighted Average Price）
        - 即股票软件分时图中的"分时均线/均价线"

    使用示例：
        >>> vwap = VWAPIndicator()
        >>> df = vwap.calculate(minute_df)  # 输出基础字段 + avg_price

    参数说明：
        无额外参数（全日累计，非滚动窗口）

    返回字段：
        avg_price: 当日分时均价（累计成交额/累计成交量）

    注意：
        - 输入必须为当日分时数据（按时间正序）
        - 价格字段自适应：优先close，缺失时用price（兼容策略层改名字段）
        - 优先使用amount字段（真实成交额）；缺失时用价格*volume估算
        - 均价线在价格线上方表示强势（大部分时间高价成交），下方为弱势
    """

    def __init__(self):
        """
        初始化分时均价线指标
        """
        super().__init__(name='VWAP', required_fields=['volume'])

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算分时均价线

        Args:
            df (DataFrame): 当日分时数据，必须包含volume字段及close（或price）字段，按时间正序

        Returns:
            DataFrame: 增强数据（基础字段 + avg_price）

        Raises:
            ValueError: 如果输入DataFrame为空

        Example:
            >>> vwap = VWAPIndicator()
            >>> minute_df = BasicMinutes().get_data('000400', '20260821')
            >>> df = vwap.calculate(minute_df)  # df新增avg_price列
        """
        if not self.validate_input(df):
            return df.copy()

        # 价格字段自适应：close 或 price
        if 'close' in df.columns:
            price = df['close']
        elif 'price' in df.columns:
            price = df['price']
        else:
            print(f"[{self.name}] 缺少必需字段: close 或 price")
            return df.copy()

        df = df.copy()

        # 成交额：优先用真实amount，缺失时用 价格*成交量 估算
        if 'amount' in df.columns:
            amount = df['amount']
        else:
            amount = price * df['volume']

        # 累计均价 = 累计成交额 / 累计成交量
        cum_amount = amount.cumsum()
        cum_volume = df['volume'].cumsum()

        df['avg_price'] = (cum_amount / cum_volume).round(3)

        return df
