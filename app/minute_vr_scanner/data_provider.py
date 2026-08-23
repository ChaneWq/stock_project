"""
数据接入层

功能：
- 封装 pystock_data 的 BasicMinutesWithVR
- 为策略提供标准输入格式（price, volume_ratio, time_index, hour, minute）
- 提供昨收价（用于涨幅计算）

数据流：
    BasicMinutesWithVR.get_data() 一次性完成：
    分时获取 + 过去n日日线成交量 + 量比计算
    输出字段：close, volume, hour, minute, volume_ratio,
             cumulative_vol, time_index, avg_vol_per_minute
    本模块适配：close → price（策略约定字段名）
"""

import pandas as pd
from pystock_data.basic import BasicMinutesWithVR


class DataProvider:
    """
    策略数据提供者

    功能：
        - 获取带量比的分时数据（一站式）
        - 适配策略所需字段名
        - 提供昨收价

    使用示例：
        >>> provider = DataProvider()
        >>> df, prev_close = provider.get_strategy_df('000400', '20260821', n=5)
        >>> # df包含 price, volume_ratio, time_index, hour, minute 字段

    注意：
        - 并发场景下每个线程应持有独立实例（内部client线程隔离）
    """

    def __init__(self):
        # thread_safe=True: 每线程独立client，避免连接冲突
        self._minutes_vr = BasicMinutesWithVR(thread_safe=True)

    def get_strategy_df(self, code: str, date: str, n: int = 5):
        """
        获取策略所需的标准分时数据

        Args:
            code (str): 股票代码（6位字符串）
            date (str): 日期（格式YYYYMMDD）
            n (int): 过去n个交易日（量比基准），默认5

        Returns:
            tuple: (策略DataFrame, 昨收价)
                获取失败时返回 (None, None)

        Example:
            >>> provider = DataProvider()
            >>> df, prev_close = provider.get_strategy_df('000400', '20260821')
        """
        vr_df = self._minutes_vr.get_data(code, date, n=n)

        if vr_df.empty:
            return None, None

        prev_close = self._minutes_vr.get_prev_close()

        # 适配策略字段名：分时数据的close即策略中的price
        df = vr_df.rename(columns={'close': 'price'})

        return df, prev_close
