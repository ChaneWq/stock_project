"""
日线指标特征提取编排模块

功能：
- 串联指标层各类式指标，计算 stock_features4 表所需的全部日线特征
- 本模块不含任何指标公式，公式统一来自 pystock_data.indicators 指标层

特征列表（22个，由指标层各类计算）：
- MACDIndicator: DIF/DEA/MACD
- KDJIndicator: K/D/J
- MAIndicator: MA5~MA250 十档均线
- BBIIndicator: BBI
- ZXTIndicator: zxt（砖型图）
- DZSIndicator/DZTIndicator: dzs/dzt（单针）
- ZXShortTermTrendIndicator/ZXBullBearLineIndicator: zx组合线

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import pandas as pd

from pystock_data.indicators import (
    MACDIndicator, KDJIndicator, MAIndicator, BBIIndicator,
    ZXTIndicator, DZSIndicator, DZTIndicator,
    ZXShortTermTrendIndicator, ZXBullBearLineIndicator,
)

# 均线周期（与表结构列一一对应）
MA_PERIODS = [5, 7, 10, 20, 30, 40, 45, 60, 90, 250]

# 输出列顺序（即表字段顺序）
OUTPUT_COLUMNS = [
    "code", "trade_date", "open", "close", "high", "low", "vol", "amount",
    "zx_short_term_trend", "zx_bull_bear_line",
    "K", "D", "J", "BBI",
    *[f"MA{n}" for n in MA_PERIODS],
    "DIF", "DEA", "MACD", "zxt", "dzs", "dzt",
]

# 指标层实例（无状态，模块级复用）
_INDICATORS = (
    MACDIndicator(),
    KDJIndicator(),
    MAIndicator(periods=MA_PERIODS),
    BBIIndicator(),
    ZXTIndicator(),
    DZSIndicator(),
    DZTIndicator(),
    ZXShortTermTrendIndicator(),
    ZXBullBearLineIndicator(),
)

# 指标层业务列名 → 表结构列名
_COLUMN_MAP = {
    'macd_dif': 'DIF', 'macd_dea': 'DEA', 'macd_macd': 'MACD',
    'kdj_k': 'K', 'kdj_d': 'D', 'kdj_j': 'J',
    'bbi': 'BBI',
    **{f'ma{n}': f'MA{n}' for n in MA_PERIODS},
}


def extract_features(code: str, daily_df: pd.DataFrame,
                     start_dt: str, end_dt: str) -> pd.DataFrame:
    """
    计算单只股票的日线指标特征（纯编排：调指标层，零公式）

    Args:
        code (str): 股票代码（6位字符串）
        daily_df (DataFrame): 日线数据（standardize_fields 标准列，
            需包含 close/high/low/open/volume/amount/trade_date）
        start_dt (str): 起始日期 'YYYY-MM-DD'
        end_dt (str): 结束日期 'YYYY-MM-DD'

    Returns:
        DataFrame: 日期窗口内的特征数据（OUTPUT_COLUMNS 列），无数据返回空DataFrame
    """
    if daily_df is None or daily_df.empty:
        return pd.DataFrame()

    # 依次执行指标层各类（每类校验输入并追加特征列）
    df = daily_df
    for indicator in _INDICATORS:
        df = indicator.calculate(df)

    # 列名映射为表结构，过滤日期窗口，规整输出列（volume → vol）
    df = df.rename(columns=_COLUMN_MAP)
    df = df[(df['trade_date'] >= start_dt) & (df['trade_date'] <= end_dt)]
    df = df.rename(columns={'volume': 'vol'})
    df['code'] = code

    return df[OUTPUT_COLUMNS]
