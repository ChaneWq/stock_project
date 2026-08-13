"""
个股监控数据采集与组装

字段口径：
    最新股价涨幅   : (日线最新收盘 - 昨收) / 昨收 * 100
    9:30 分量比     : BasicMinutesWithVR 返回第 1 行 volume_ratio
    最新量比        : BasicMinutesWithVR 返回最后一行 volume_ratio（最新分钟）
    9:30 分涨幅     : (9:30 价 - 昨收) / 昨收 * 100
    9:31 分涨幅     : (9:31 价 - 昨收) / 昨收 * 100
    ma7 股价        : 日线最新行 ma7
    最新价格        : 日线最新收盘
    距离 ma7%       : (最新价 - ma7) / ma7 * 100

性能优化：
    - 日线缓存：日线数据日内不变，首次请求后缓存，后续刷新读缓存（省 N 次请求）
    - 请求间隔：每只股票之间加 REQUEST_INTERVAL 秒间隔，防止请求过快触发限流
    - 数据源对象在 collect_all 中创建一次复用

说明：
    - 昨收优先取 BasicMinutesWithVR.get_prev_close()，取不到时用日线第 2 行 close 兜底
    - 当日非交易日或分时获取失败时，分时相关字段为 None（前端显示 -），日线字段仍展示
    - 单只采集异常不中断整体流程
"""

import time
import pandas as pd
from datetime import datetime

from pystock_data import BasicBars, BasicMinutesWithVR, MAIndicator

from .config import REQUEST_INTERVAL, DAILY_CACHE_ENABLED


# 日线数据缓存：key=(code, date_str)，value=daily_df
# 日内有效（date 变了自动 miss），不主动清理（股票数量有限，内存可控）
_daily_cache = {}


def _get_daily_cached(bars, code, date_str):
    """
    获取日线数据（带日内缓存）

    日线数据日内不变，首次请求后缓存，后续刷新直接读缓存。
    缓存 key 含 date_str，换天后自动 miss 重新请求。

    Args:
        bars (BasicBars): 复用实例
        code (str): 股票代码
        date_str (str): 查询日期 YYYYMMDD（用于缓存隔离）

    Returns:
        DataFrame: 日线数据
    """
    if DAILY_CACHE_ENABLED:
        key = (code, date_str)
        if key in _daily_cache:
            return _daily_cache[key]

    df = bars.get_daily(code, 30)

    if DAILY_CACHE_ENABLED:
        _daily_cache[(code, date_str)] = df
    return df


def clear_daily_cache():
    """清空日线缓存（主要用于测试或强制刷新）"""
    _daily_cache.clear()


def _safe_pct(numerator, denominator):
    """安全计算百分比，失败返回 None"""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round((numerator - denominator) / denominator * 100, 2)


def _round2(v):
    """数值保留两位小数，None 透传"""
    return None if v is None else round(float(v), 2)


def _collect_one(stock, date, bars, vr, ma_indicator):
    """
    采集单只股票数据

    Args:
        stock (dict): {'code','name','remark','category'}
        date (str): 查询日期 YYYYMMDD
        bars (BasicBars): 复用实例
        vr (BasicMinutesWithVR): 复用实例
        ma_indicator (MAIndicator): 复用实例

    Returns:
        dict: 单条记录
    """
    code = stock['code']
    name = stock.get('name', '')
    remark = stock.get('remark', '')
    category = stock.get('category', '')

    result = {
        'code': code,
        'name': name,
        'remark': remark,
        'category': category,
        'latest_price': None,
        'price_change_pct': None,
        'vr_930': None,
        'vr_latest': None,
        'change_930_pct': None,
        'change_931_pct': None,
        'ma7': None,
        'dev_ma7_pct': None,
    }

    # 1) 日线：最新价、昨收兜底、ma7（带日内缓存）
    try:
        daily_df = _get_daily_cached(bars, code, date)
    except Exception as e:
        print(f"[monitor] {code} 获取日线失败: {e}")
        daily_df = pd.DataFrame()

    prev_close_from_daily = None
    if not daily_df.empty:
        # get_daily 倒序：第1行最新，第2行昨日
        latest_row = daily_df.iloc[0]
        result['latest_price'] = _round2(latest_row['close'])

        if len(daily_df) >= 2:
            prev_close_from_daily = float(daily_df.iloc[1]['close'])
            result['price_change_pct'] = _safe_pct(
                float(latest_row['close']), prev_close_from_daily
            )

        # ma7 需按时间正序计算
        asc_df = daily_df.iloc[::-1].reset_index(drop=True)
        ma_df = ma_indicator.calculate(asc_df)
        result['ma7'] = _round2(ma_df.iloc[-1]['ma7'])
        result['dev_ma7_pct'] = _safe_pct(result['latest_price'], result['ma7'])

    # 2) 分时带量比：9:30/9:31 行 + 量比 + prev_close
    try:
        vr_df = vr.get_data(code, date, n=5)
    except Exception as e:
        print(f"[monitor] {code} 获取分时失败: {e}")
        vr_df = pd.DataFrame()

    if not vr_df.empty and len(vr_df) >= 2:
        prev_close = vr.get_prev_close()
        # prev_close 取不到时用日线兜底
        if prev_close is None:
            prev_close = prev_close_from_daily

        row_930 = vr_df.iloc[0]
        row_931 = vr_df.iloc[1]

        result['vr_930'] = _round2(row_930['volume_ratio'])
        result['vr_latest'] = _round2(vr_df.iloc[-1]['volume_ratio'])
        if prev_close is not None:
            result['change_930_pct'] = _safe_pct(float(row_930['close']), prev_close)
            result['change_931_pct'] = _safe_pct(float(row_931['close']), prev_close)

    return result


def collect_all(stocks, date=None):
    """
    采集所有股票数据

    Args:
        stocks (list[dict]): [{'code','name','remark','category'}, ...]
        date (str, optional): 查询日期 YYYYMMDD，默认当日

    Returns:
        list[dict]: 每只股票一条记录
    """
    date = date or datetime.now().strftime('%Y%m%d')
    total = len(stocks)
    print(f"[monitor] 开始采集 {total} 只股票 (date={date}) ...")
    t_start = time.time()

    # 数据源对象只创建一次，循环复用（避免每只股票重复实例化）
    bars = BasicBars()
    vr = BasicMinutesWithVR()
    ma_indicator = MAIndicator(periods=[7])

    results = []
    for i, stock in enumerate(stocks):
        # 请求间隔：第一只不间隔，后续每只之间加间隔，防止请求过快触发限流
        if i > 0 and REQUEST_INTERVAL > 0:
            time.sleep(REQUEST_INTERVAL)

        code = stock.get('code', '')
        name = stock.get('name', '')
        print(f"[monitor] 采集 {code} {name} (date={date}) ...")
        try:
            r = _collect_one(stock, date, bars, vr, ma_indicator)
        except Exception as e:
            print(f"[monitor] {code} {name} 采集异常: {e}")
            r = {
                'code': code, 'name': name, 'remark': stock.get('remark', ''),
                'category': stock.get('category', ''),
                'latest_price': None, 'price_change_pct': None,
                'vr_930': None, 'vr_latest': None,
                'change_930_pct': None, 'change_931_pct': None,
                'ma7': None, 'dev_ma7_pct': None,
            }
        results.append(r)

    t_cost = time.time() - t_start
    print(f"[monitor] 采集完成：{len(results)}/{total} 只，耗时 {t_cost:.2f}s")
    return results
