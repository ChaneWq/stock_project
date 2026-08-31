"""
分钟量比特征提取模块

功能：
- 基于 BasicMinutesWithVR 获取分时量比数据
- 提取 09:30/09:31/09:32 的量比与价格特征（共6个字段）

复用说明：
- 分钟数据获取/过去5日基准量/量比计算全部复用 pystock_data.basic.BasicMinutesWithVR，
  不再引入外部 minute_vr_fetcher / minute_vr_calc 模块

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import pandas as pd

from pystock_data.basic import BasicMinutesWithVR

# 分钟特征字段（即表字段）
MINUTE_FEATURE_FIELDS = [
    'vol_ratio_0930', 'vol_ratio_0931', 'vol_ratio_0932',
    'price_0930', 'price_0931', 'price_0932',
]

# 空/失败时的特征值
_EMPTY_FEATURES = {field: None for field in MINUTE_FEATURE_FIELDS}


class MinuteFeatureFetcher:
    """
    分钟量比特征提取器

    使用示例：
        >>> fetcher = MinuteFeatureFetcher(thread_safe=True)
        >>> features = fetcher.get_features('000400', '2026-08-28', daily_df)
    """

    def __init__(self, market: str = 'std', thread_safe: bool = False, n_days: int = 5):
        """
        Args:
            market (str): 通达信市场参数，默认'std'
            thread_safe (bool): 多线程场景设为 True（线程独立 client）
            n_days (int): 量比基准的过去交易日数，默认5
        """
        self.minutes_vr = BasicMinutesWithVR(market=market, thread_safe=thread_safe)
        self.n_days = n_days

    def get_features(self, code: str, trade_date: str,
                     daily_df: pd.DataFrame = None) -> dict:
        """
        获取指定交易日的分钟量比特征

        Args:
            code (str): 股票代码（6位字符串）
            trade_date (str): 交易日期 'YYYY-MM-DD'
            daily_df (DataFrame, optional): 已持有的日线数据（含 volume/trade_date 列）。
                传入时从中提取过去n日成交量作为基准（省一次网络请求）；
                None则由数据层自动获取。

        Returns:
            dict: 6个特征字段；无数据或异常时值为 None
        """
        try:
            # '2026-01-15' → '20260115'
            date = trade_date.replace('-', '')

            # 从已持有的日线数据提取基准量（性能优化：跳过重复网络请求）
            prev_vol_list = None
            if daily_df is not None and not daily_df.empty:
                d = daily_df.copy()
                d['vol'] = d['volume']
                prev = d[d['trade_date'] < trade_date].tail(self.n_days)
                if len(prev) == self.n_days:
                    prev_vol_list = prev['vol'].tolist()

            vr_df = self.minutes_vr.get_data(code, date, n=self.n_days,
                                             prev_day_vol_list=prev_vol_list)

            if vr_df is None or vr_df.empty or len(vr_df) < 3:
                return dict(_EMPTY_FEATURES)

            # 分时数据按时间升序，前3行即 09:30 / 09:31 / 09:32
            first3 = vr_df.head(3)
            return {
                'vol_ratio_0930': float(first3['volume_ratio'].iloc[0]),
                'vol_ratio_0931': float(first3['volume_ratio'].iloc[1]),
                'vol_ratio_0932': float(first3['volume_ratio'].iloc[2]),
                'price_0930': round(float(first3['close'].iloc[0]), 3),
                'price_0931': round(float(first3['close'].iloc[1]), 3),
                'price_0932': round(float(first3['close'].iloc[2]), 3),
            }
        except Exception:
            return dict(_EMPTY_FEATURES)


def attach_minute_features(features_df: pd.DataFrame,
                           fetcher: MinuteFeatureFetcher,
                           daily_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    为日线特征数据逐行附加分钟量比特征

    Args:
        features_df (DataFrame): extract_features 输出
        fetcher (MinuteFeatureFetcher): 分钟特征提取器（调用方线程持有）
        daily_df (DataFrame, optional): 已持有的日线数据（基准量复用，省网络请求）

    Returns:
        DataFrame: 追加6个分钟特征列后的 DataFrame
    """
    if features_df.empty:
        result = features_df.copy()
        for field in MINUTE_FEATURE_FIELDS:
            result[field] = pd.Series(dtype='float64')
        return result

    rows = [
        fetcher.get_features(code, trade_date, daily_df)
        for code, trade_date in zip(features_df['code'], features_df['trade_date'])
    ]
    minute_df = pd.DataFrame(rows, index=features_df.index)
    return pd.concat([features_df, minute_df], axis=1)
