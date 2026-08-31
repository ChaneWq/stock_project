"""
成交量均线指标计算模块

功能：
- 计算成交量均线（VMA5、VMA10等）
- 输入基础DataFrame，输出增强DataFrame
- 使用标准算法计算成交量均线

作者：PyStock项目组
日期：2026-08-24
版本：1.0.0
"""

import pandas as pd
from typing import List
from .base import IndicatorBase
from .tdx import MA as tdx_MA


class VolumeMAIndicator(IndicatorBase):
    """
    成交量均线指标计算类

    功能：
        - 计算多条成交量均线（VMA5、VMA10等）
        - 输入基础DataFrame，输出增强DataFrame

    使用示例：
        >>> vma = VolumeMAIndicator()
        >>> vma_df = vma.calculate(basic_df)

    参数说明：
        periods: 均线周期列表，默认[5]

    返回字段：
        vma5: 5日成交量均线
        vma10: 10日成交量均线（若指定）

    注意：
        - 输入DataFrame必须包含volume字段
        - 成交量均线用于判断放量/缩量（当日成交量与vma5的比值）
    """

    def __init__(self, periods: List[int] = None):
        """
        初始化成交量均线指标

        Args:
            periods (List[int], optional): 均线周期列表，默认为[5]
        """
        super().__init__(name='VMA', required_fields=['volume'])
        self.periods = periods or [5]

    def calculate(self, df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """
        计算成交量均线指标

        Args:
            df (DataFrame): 基础数据，必须包含volume字段
            periods (List[int], optional): 均线周期列表
                None - 使用初始化时设置的periods（默认[5]）
                List[int] - 使用运行时传入的自定义周期列表

        Returns:
            DataFrame: 增强数据（基础字段 + vma字段）

        Raises:
            ValueError: 如果输入DataFrame缺少必需字段或periods参数不合法

        Example:
            # 使用默认周期
            >>> vma = VolumeMAIndicator()
            >>> vma_df = vma.calculate(basic_df)  # 输出vma5

            # 运行时动态指定周期
            >>> vma = VolumeMAIndicator()
            >>> df1 = vma.calculate(basic_df, periods=[5, 10])  # 输出vma5、vma10

        Note:
            - periods参数支持运行时动态传入，无需重新创建实例
            - 向后兼容：periods=None时使用初始化设置的周期
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

        # 计算各周期成交量均线
        for period in use_periods:
            # 公式来源：tdx 公式函数库 MA（标准滚动均值，前 N-1 行为 NaN）
            vma = pd.Series(tdx_MA(df['volume'].values, period), index=df.index)
            # 前 period-1 行用部分窗口均值补齐（保持历史行为：min_periods=1）
            vma = vma.fillna(df['volume'].expanding().mean())
            # 成交量均线字段名：vma5, vma10等
            field_name = f'vma{period}'
            # 保留两位小数
            df[field_name] = vma.round(2)

        return df

    def get_periods(self) -> List[int]:
        """
        获取均线周期列表

        Returns:
            List[int]: 均线周期列表

        Example:
            >>> vma = VolumeMAIndicator()
            >>> periods = vma.get_periods()
        """
        return self.periods
