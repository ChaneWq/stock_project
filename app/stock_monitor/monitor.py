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
    - 批量间隔：每 BATCH_SIZE 只后间隔 BATCH_INTERVAL 秒，防止请求过快触发限流
    - 并发采集：ThreadPoolExecutor 多线程并发，每线程独立 client（threading.local）
    - 数据源对象按线程缓存复用

说明：
    - 昨收优先取 BasicMinutesWithVR.get_prev_close()，取不到时用日线第 2 行 close 兜底
    - 当日非交易日或分时获取失败时，分时相关字段为 None（前端显示 -），日线字段仍展示
    - 单只采集异常不中断整体流程
"""

import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from datetime import datetime

from pystock_data import BasicBars, BasicMinutesWithVR, MAIndicator

from .config import BATCH_SIZE, BATCH_INTERVAL, DAILY_CACHE_ENABLED, MAX_WORKERS


# 日线数据缓存：key=(code, date_str)，value=daily_df
# 日内有效（date 变了自动 miss），不主动清理（股票数量有限，内存可控）
_daily_cache = {}
_cache_lock = threading.Lock()


def _get_daily_cached(bars, code, date_str):
    """
    获取日线数据（带日内缓存，线程安全）

    日线数据日内不变，首次请求后缓存，后续刷新直接读缓存。
    缓存 key 含 date_str，换天后自动 miss 重新请求。
    多线程并发时用 _cache_lock 保护 dict 读写。

    Args:
        bars (BasicBars): 复用实例
        code (str): 股票代码
        date_str (str): 查询日期 YYYYMMDD（用于缓存隔离）

    Returns:
        DataFrame: 日线数据
    """
    if DAILY_CACHE_ENABLED:
        key = (code, date_str)
        with _cache_lock:
            if key in _daily_cache:
                return _daily_cache[key]

    df = bars.get_daily(code, 30)

    if DAILY_CACHE_ENABLED:
        with _cache_lock:
            _daily_cache[(code, date_str)] = df
    return df


def clear_daily_cache():
    """清空日线缓存（主要用于测试或强制刷新）"""
    with _cache_lock:
        _daily_cache.clear()


# 线程独立数据源：每个线程拥有独立的 BasicBars/BasicMinutesWithVR/MAIndicator
# thread_safe=True 使底层 client 也线程独立（基于 ClientManager.get_thread_client）
_thread_local = threading.local()


def _get_thread_resources():
    """
    获取当前线程的数据源（线程独立，首次调用时创建）

    每个线程首次调用时创建独立的数据源实例（含独立 client），
    后续调用直接返回缓存实例，避免重复创建。

    Returns:
        tuple: (bars, vr, ma_indicator)
    """
    if not hasattr(_thread_local, 'bars'):
        _thread_local.bars = BasicBars(thread_safe=True)
        _thread_local.vr = BasicMinutesWithVR(thread_safe=True)
        _thread_local.ma = MAIndicator(periods=[7])
    return _thread_local.bars, _thread_local.vr, _thread_local.ma


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
    # 分时查询日期：默认用传入 date，日线有数据时改用日线最新行日期（最近交易日）
    minute_date = date
    if not daily_df.empty:
        latest_row = daily_df.iloc[0]
        # 从日线最新行取分时查询日期（解决非交易日/盘前运行时取不到分时的问题）
        if 'trade_date' in daily_df.columns:
            trade_date = str(latest_row['trade_date'])[:10].replace('-', '')
            if trade_date:
                minute_date = trade_date
        # 昨收兜底：日线第2行 close
        if len(daily_df) >= 2:
            prev_close_from_daily = float(daily_df.iloc[1]['close'])

    # 2) 分时带量比：最新价、量比、9:30/9:31 涨幅（每次刷新实时获取）
    try:
        vr_df = vr.get_data(code, minute_date, n=5)
    except Exception as e:
        print(f"[monitor] {code} 获取分时失败: {e}")
        vr_df = pd.DataFrame()

    latest_price = None
    prev_close = None
    if not vr_df.empty and len(vr_df) >= 2:
        prev_close = vr.get_prev_close()
        if prev_close is None:
            prev_close = prev_close_from_daily

        row_930 = vr_df.iloc[0]
        row_931 = vr_df.iloc[1]
        # 最新价：分时最新行 close（实时）
        latest_price = _round2(vr_df.iloc[-1]['close'])

        result['vr_930'] = _round2(row_930['volume_ratio'])
        result['vr_latest'] = _round2(vr_df.iloc[-1]['volume_ratio'])
        if prev_close is not None:
            result['change_930_pct'] = _safe_pct(float(row_930['close']), prev_close)
            result['change_931_pct'] = _safe_pct(float(row_931['close']), prev_close)

    # 分时取不到最新价时，用日线兜底
    if latest_price is None and not daily_df.empty:
        latest_price = _round2(daily_df.iloc[0]['close'])
    result['latest_price'] = latest_price

    # 涨幅基于实时最新价和昨收
    if latest_price is not None and prev_close is not None:
        result['price_change_pct'] = _safe_pct(latest_price, prev_close)
    elif latest_price is not None and prev_close_from_daily is not None:
        result['price_change_pct'] = _safe_pct(latest_price, prev_close_from_daily)

    # 3) ma7：历史 close（日线缓存）+ 最新价用分时替换，使 ma7 反映盘中实时价
    if not daily_df.empty:
        asc_df = daily_df.iloc[::-1].reset_index(drop=True)
        if latest_price is not None:
            asc_df.iloc[-1, asc_df.columns.get_loc('close')] = float(latest_price)
        ma_df = ma_indicator.calculate(asc_df)
        result['ma7'] = _round2(ma_df.iloc[-1]['ma7'])
        result['dev_ma7_pct'] = _safe_pct(latest_price, result['ma7'])

    return result


def _collect_one_safe(stock, date):
    """
    采集单只股票（并发安全包装，异常不外抛）

    从线程本地存储获取数据源，调用 _collect_one，异常时返回兜底记录。

    Args:
        stock (dict): 股票配置
        date (str): 查询日期 YYYYMMDD

    Returns:
        dict: 单条记录（异常时为全 None 兜底）
    """
    code = stock.get('code', '')
    name = stock.get('name', '')
    print(f"[monitor] 采集 {code} {name} ...")
    try:
        bars, vr, ma = _get_thread_resources()
        return _collect_one(stock, date, bars, vr, ma)
    except Exception as e:
        print(f"[monitor] {code} {name} 采集异常: {e}")
        return {
            'code': code, 'name': name, 'remark': stock.get('remark', ''),
            'category': stock.get('category', ''),
            'latest_price': None, 'price_change_pct': None,
            'vr_930': None, 'vr_latest': None,
            'change_930_pct': None, 'change_931_pct': None,
            'ma7': None, 'dev_ma7_pct': None,
        }


def collect_all(stocks, date=None):
    """
    采集所有股票数据（并发）

    使用 ThreadPoolExecutor 并发采集，每线程独立 client（thread_safe=True）。
    提交时按 BATCH_SIZE 控制速率（每 BATCH_SIZE 只间隔 BATCH_INTERVAL 秒），
    防止整体请求过快触发限流；用 as_completed 收集结果，不阻塞等待整批。

    Args:
        stocks (list[dict]): [{'code','name','remark','category'}, ...]
        date (str, optional): 查询日期 YYYYMMDD，默认当日

    Returns:
        list[dict]: 每只股票一条记录（顺序与输入一致）
    """
    date = date or datetime.now().strftime('%Y%m%d')
    total = len(stocks)
    print(f"[monitor] 开始采集 {total} 只股票 (date={date}, max_workers={MAX_WORKERS}) ...")
    t_start = time.time()

    results = [None] * total

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {}
        for idx, stock in enumerate(stocks):
            # 提交速率控制：每 BATCH_SIZE 只后间隔
            if idx > 0 and idx % BATCH_SIZE == 0 and BATCH_INTERVAL > 0:
                time.sleep(BATCH_INTERVAL)
            f = pool.submit(_collect_one_safe, stock, date)
            futures[f] = idx

        # as_completed 收集结果（哪个先完成就先取，不阻塞等待整批）
        for f in as_completed(futures):
            results[futures[f]] = f.result()

    t_cost = time.time() - t_start
    print(f"[monitor] 采集完成：{total}/{total} 只，耗时 {t_cost:.2f}s")
    return results
