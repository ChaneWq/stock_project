"""
个股数据查询模块（本地 pystock_data 数据源版）

功能：
- 按 code + 日期区间（或最近N个交易日）查询个股日线数据
- 每个交易日附加分时量比/分时价格（9:30、9:31）
- 计算派生字段：涨幅、成交量变化%、MA7、收盘价与MA7偏离度、9:30/9:31涨幅

数据源：本地 pystock_data（TdxSource，通达信）

字段口径：
    涨幅        : (close - 昨收) / 昨收 * 100
    成交量变化%  : (vol - prev_vol) / prev_vol * 100
    MA7         : 含当日的7日均线
    偏离度%     : (close - MA7) / MA7 * 100
    9:30量比    : 分时第1行 volume_ratio
    9:30涨幅%   : (分时第1行 close - 昨收) / 昨收 * 100（9:31 同理）

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import os
import sys
import threading
from datetime import datetime

import pandas as pd

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from pystock_data import BasicBars, BasicMinutesWithVR, MAIndicator

# 数据源实例（懒加载单例；线程独立 client，便于后续并发扩展）
_local = threading.local()


def _get_resources():
    """获取数据源实例（首次调用时创建）"""
    if not hasattr(_local, 'bars'):
        _local.bars = BasicBars()
        _local.vr = BasicMinutesWithVR()
        _local.ma = MAIndicator(periods=[7])
    return _local.bars, _local.vr, _local.ma


def _safe_pct(new, old):
    """安全计算百分比 (new-old)/old*100，失败返回 None"""
    if new is None or old is None or pd.isna(new) or pd.isna(old) or old == 0:
        return None
    return round((float(new) - float(old)) / float(old) * 100, 2)


def _round(v, digits=3):
    """数值保留N位小数，None/NaN 透传"""
    if v is None or pd.isna(v):
        return None
    return round(float(v), digits)


def query_stock(code: str, start_date: str = None, end_date: str = None,
                recent_days: int = None) -> list:
    """
    查询个股数据

    Args:
        code (str): 股票代码，如 '000712'
        start_date (str, optional): 开始日期 YYYY-MM-DD（区间模式）
        end_date (str, optional): 结束日期 YYYY-MM-DD（区间模式，默认今天）
        recent_days (int, optional): 最近N个交易日（优先于区间模式）

    Returns:
        list[dict]: 按交易日倒序的记录
    """
    code = str(code).strip()
    if not code or len(code) != 6 or not code.isdigit():
        raise ValueError(f"股票代码格式错误：{code}（应为6位数字）")

    bars, vr, ma_indicator = _get_resources()

    # 1) 日线：拉足够多的天数（区间跨度 + 10天余量供均线/昨收计算）
    if recent_days:
        n_days = int(recent_days) + 10
    else:
        end = end_date or datetime.now().strftime('%Y-%m-%d')
        start = start_date or end
        span = (pd.Timestamp(end) - pd.Timestamp(start)).days
        n_days = max(span + 30, 40)  # 区间跨度 + 30天余量（含均线预热）

    daily_df = bars.get_daily(code, n_days)
    if daily_df is None or daily_df.empty:
        raise ValueError(f"股票 {code} 未获取到日线数据（代码不存在或数据源异常）")

    # 2) 时间过滤：日线是倒序（最新在前），含 trade_date 列
    asc_df = daily_df.iloc[::-1].reset_index(drop=True)

    if start_date:
        asc_df = asc_df[asc_df['trade_date'] >= start_date]
    if end_date:
        asc_df = asc_df[asc_df['trade_date'] <= end_date]
    asc_df = asc_df.reset_index(drop=True)

    if recent_days:
        asc_df = asc_df.tail(int(recent_days)).reset_index(drop=True)

    if asc_df.empty:
        return []

    # 3) MA7：全量日线（倒序）算均线后，按 trade_date 对齐取查询区间内的值
    ma_full = ma_indicator.calculate(daily_df.iloc[::-1].reset_index(drop=True))

    records = []
    for i in range(len(asc_df)):
        row = asc_df.iloc[i]
        prev_row = asc_df.iloc[i - 1] if i > 0 else None
        trade_date = str(row['trade_date'])[:10].replace('-', '')  # YYYYMMDD

        # 昨收/昨量：优先取前一行，无前一行时从全量日线里找
        prev_close = float(prev_row['close']) if prev_row is not None else None
        prev_vol = float(prev_row['volume']) if prev_row is not None else None
        if prev_close is None:
            # 区间首日：在日线里找 trade_date 之前最近一行
            idx = daily_df[daily_df['trade_date'] == row['trade_date']].index
            if len(idx) > 0 and idx[0] + 1 < len(daily_df):
                prev_row_full = daily_df.iloc[idx[0] + 1]  # 倒序，+1 为前一交易日
                prev_close = float(prev_row_full['close'])
                prev_vol = float(prev_row_full['volume'])

        # MA7：从均线结果里对齐当日
        ma_row = ma_full[ma_full['trade_date'] == row['trade_date']]
        ma7 = float(ma_row.iloc[-1]['ma7']) if not ma_row.empty and not pd.isna(ma_row.iloc[-1]['ma7']) else None

        # 分时：9:30/9:31 量比与价格（失败不中断，字段置 None）
        vr_930 = vr_931 = price_930 = price_931 = None
        try:
            vr_df = vr.get_data(code, trade_date, n=5)
            if not vr_df.empty and len(vr_df) >= 2:
                vr_930 = _round(vr_df.iloc[0]['volume_ratio'])
                vr_931 = _round(vr_df.iloc[1]['volume_ratio'])
                price_930 = _round(vr_df.iloc[0]['close'], 2)
                price_931 = _round(vr_df.iloc[1]['close'], 2)
        except Exception:
            pass

        close = _round(row['close'], 2)
        vol = int(row['volume'])

        records.append({
            'trade_date': str(row['trade_date'])[:10],
            'today_rate': _safe_pct(row['close'], prev_close),
            'vol': vol,
            'vol_chg_pct': _safe_pct(vol, prev_vol),
            'MA7': _round(ma7, 3) if ma7 is not None else None,
            'dev_pct': _safe_pct(close, ma7),
            'vol_ratio_0930': vr_930,
            'rate_0930': _safe_pct(price_930, prev_close),
            'vol_ratio_0931': vr_931,
            'rate_0931': _safe_pct(price_931, prev_close),
        })

    return records[::-1]  # 倒序返回（最新在前）


def query_minutes(code: str, query_date: str) -> list:
    """
    查询某交易日的全天分时数据（240行，9:30~14:59 正序）

    Args:
        code (str): 股票代码，如 '000712'
        query_date (str): 日期 YYYY-MM-DD

    Returns:
        list[dict]: 分时记录（时间/价格/涨幅/分钟量/累计量/量比）
    """
    code = str(code).strip()
    if not code or len(code) != 6 or not code.isdigit():
        raise ValueError(f"股票代码格式错误：{code}（应为6位数字）")

    query_date = (query_date or '').strip()
    try:
        ts = pd.Timestamp(query_date)
        if pd.isna(ts):
            raise ValueError(query_date)
    except Exception:
        raise ValueError(f"日期格式错误：{query_date}（应为 YYYY-MM-DD）")
    date_str = ts.strftime('%Y%m%d')

    bars, vr, _ = _get_resources()

    # 昨收：按查询日期动态拉日线（距今越远拉越多，跨度+40根余量），
    # 取查询日之前最近一个交易日的收盘价（日线倒序，首行即最近）
    prev_close = None
    span = max((datetime.now() - ts).days, 0)
    daily_df = bars.get_daily(code, span + 40)
    if daily_df is not None and not daily_df.empty:
        td_list = daily_df['trade_date'].astype(str).str[:10].str.replace('-', '')
        before_idx = td_list[td_list < date_str].index
        if len(before_idx) > 0:
            prev_close = float(daily_df.loc[before_idx[0], 'close'])

    # 全天分时（含量比），n=5 为量比基准天数
    vr_df = vr.get_data(code, date_str, n=5)
    if vr_df is None or vr_df.empty:
        return []

    records = []
    for _, row in vr_df.iterrows():
        price = _round(row['close'], 2)
        records.append({
            'time': f"{int(row['hour']):02d}:{int(row['minute']):02d}",
            'price': price,
            'rate_pct': _safe_pct(price, prev_close),
            'volume': int(row['volume']),
            'cumulative_vol': int(row['cumulative_vol']),
            'volume_ratio': _round(row['volume_ratio'], 2),
        })
    return records
