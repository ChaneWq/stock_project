"""
扫描引擎

功能：
- 并发扫描股票列表（ThreadPoolExecutor + 线程独立client）
- 批量间隔控制（防止API限流）
- 数据接入走本地 pystock_data（DataProvider）

并发设计（复用 stock_monitor 已验证模式）：
- MAX_WORKERS 个线程并发
- 每线程通过 threading.local 持有独立 DataProvider（内部client隔离）
- 每 BATCH_SIZE 只暂停 BATCH_INTERVAL 秒
"""

import os
import time
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from pystock_data.basic import BasicBars
from pystock_data.indicators import VWAPIndicator

from . import config
from .data_provider import DataProvider
from .strategies import get_strategy

# 线程本地存储：每线程独立DataProvider（client隔离，_prev_close缓存不竞争）
_local = threading.local()

# 分时均价指标（纯计算无状态，模块级复用）
_vwap = VWAPIndicator()

# 进度显示锁
_print_lock = threading.Lock()


def get_latest_trade_date(codes, try_count=5):
    """
    用日线最新trade_date作为默认扫描日期

    处理非交易日运行：今天无分时数据时，自动回退到最近一个交易日

    Args:
        codes: 股票代码列表（取前try_count只依次尝试，防个别股票数据异常）
        try_count: 最多尝试的股票数

    Returns:
        str: 交易日期（YYYYMMDD），全部失败时回退到今天
    """
    try:
        bars = BasicBars()
        for code in codes[:try_count]:
            df = bars.get_daily(code, 1)
            if not df.empty:
                # get_daily最新在第一行；trade_date格式YYYY-MM-DD
                trade_date = str(df.iloc[0]['trade_date'])[:10].replace('-', '')
                if trade_date:
                    return trade_date
    except Exception as e:
        with _print_lock:
            print(f"\n[Warning] 获取最新交易日失败: {e}，回退使用今天")
    return datetime.now().strftime('%Y%m%d')


def _get_provider() -> DataProvider:
    """获取当前线程的DataProvider（懒加载，线程间隔离）"""
    if not hasattr(_local, 'provider'):
        _local.provider = DataProvider()
    return _local.provider


def scan(codes, date, strategy_id, n=5, until_hour=None, until_minute=None,
         change_min=-100, change_max=100, progress_callback=None, **strategy_kwargs):
    """
    并发扫描股票列表，按策略评分

    参数:
        codes: 股票代码列表
        date: 日期，格式 '20260519'
        strategy_id: 策略ID（vr_slope / vr_anomaly）
        n: 过去n个交易日，默认5
        until_hour: 截至时间-小时，None表示全天
        until_minute: 截至时间-分钟，None表示全天
        change_min: 涨幅下限(%)，默认-100不限
        change_max: 涨幅上限(%)，默认100不限
        progress_callback: 进度回调 callback(done, total)，None则打印进度（CLI行为）
        **strategy_kwargs: 策略参数，透传给策略的evaluate函数

    返回:
        list[dict]: 命中结果，按 score 降序排列
    """
    strategy_fn = get_strategy(strategy_id)
    results = []
    total = len(codes)
    done_count = [0]  # 闭包可变计数

    def worker(code):
        try:
            return _scan_single(code, date, strategy_fn, n, until_hour, until_minute,
                                change_min, change_max, **strategy_kwargs)
        except Exception as e:
            if progress_callback is None:
                with _print_lock:
                    print(f"\n[Error] {code}: {e}")
            return None

    def on_done(future):
        result = future.result()
        if result is not None:
            results.append(result)
        with _print_lock:
            done_count[0] += 1
            if progress_callback is not None:
                progress_callback(done_count[0], total)
            else:
                print(f"\r扫描中: {done_count[0]}/{total}", end='', flush=True)

    with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
        # 分批提交：每批之间间隔，防请求过快
        for i in range(0, total, config.BATCH_SIZE):
            batch = codes[i:i + config.BATCH_SIZE]
            futures = [executor.submit(worker, code) for code in batch]
            for future in as_completed(futures):
                on_done(future)
            if config.BATCH_INTERVAL > 0 and i + config.BATCH_SIZE < total:
                time.sleep(config.BATCH_INTERVAL)

    if progress_callback is None:
        print()  # 换行

    # 按综合评分降序
    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def get_minute_detail(code, date, n=5):
    """
    获取单只股票分时明细（供Web图表展示）

    复用量比基准缓存与DataProvider，与扫描同数据源。

    Args:
        code: 股票代码
        date: 日期（YYYYMMDD）
        n: 过去n个交易日（量比基准）

    Returns:
        dict: {
            'time': ['09:30', ...],
            'price': [...],
            'avg_price': [...],          # 分时均价线（VWAP）
            'volume_ratio': [...],
            'prev_close': float,
            'avg_vol_per_minute': float
        }
        失败返回 None
    """
    try:
        provider = _get_provider()
        df, prev_close = provider.get_strategy_df(code, date, n)
        if df is None:
            return None

        # 分时均价线（累计成交额/累计成交量）
        df = _vwap.calculate(df)

        # 拼时间字符串 HH:MM
        times = ["%02d:%02d" % (int(h), int(m)) for h, m in zip(df['hour'], df['minute'])]

        return {
            'time': times,
            'price': [round(float(p), 3) for p in df['price']],
            'avg_price': [round(float(p), 3) for p in df['avg_price']],
            'volume_ratio': [round(float(v), 3) for v in df['volume_ratio']],
            'prev_close': round(float(prev_close), 3),
            'avg_vol_per_minute': round(float(df['avg_vol_per_minute'].iloc[0]), 3),
        }
    except Exception:
        return None


def _scan_single(code, date, strategy_fn, n, until_hour=None, until_minute=None,
                 change_min=-100, change_max=100, **strategy_kwargs):
    """扫描单只股票（工作线程内执行，使用线程独立DataProvider）"""
    provider = _get_provider()

    # 获取带量比的分时数据 + 昨收价
    minute_df, prev_close = provider.get_strategy_df(code, date, n)
    if minute_df is None or prev_close is None:
        return None

    # 截至时间截断
    if until_hour is not None and until_minute is not None:
        mask = (minute_df['hour'].astype(int) < until_hour) | \
               ((minute_df['hour'].astype(int) == until_hour) & (minute_df['minute'].astype(int) <= until_minute))
        minute_df = minute_df[mask].reset_index(drop=True)
        if minute_df.empty:
            return None

    # 执行策略评估
    eval_result = strategy_fn(minute_df, **strategy_kwargs)
    if eval_result is None:
        return None

    # 计算涨幅
    latest_price = minute_df['price'].iloc[-1]
    change_pct = (latest_price - prev_close) / prev_close * 100

    # 涨幅范围过滤
    if change_pct < change_min or change_pct > change_max:
        return None

    eval_result['code'] = code
    eval_result['date'] = date
    eval_result['change_pct'] = round(change_pct, 2)
    return eval_result


def print_results(results, strategy_id, date):
    """打印扫描结果"""
    if not results:
        print(f"\n策略: {strategy_id}  日期: {date}  命中: 0只")
        return

    print(f"\n策略: {strategy_id}  日期: {date}  命中: {len(results)}只")

    if strategy_id == 'vr_anomaly':
        _print_anomaly(results)
    else:
        _print_slope(results)


def _print_slope(results):
    """vr_slope 策略输出"""
    print("-" * 130)
    print(f"{'排名':>4}  {'代码':<8}  {'综合评分':>8}  {'量比斜率':>8}  {'命中窗口':>8}  {'涨幅':>8}  {'价格斜率':>10}  {'命中时段'}")
    print("-" * 130)

    for i, r in enumerate(results):
        chg = r['change_pct']
        chg_str = f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"
        print(f"{i+1:>4}  {r['code']:<8}  {r['score']:>8.4f}  {r['avg_vr_slope_deg']:>6.1f}°  "
              f"{r['hit_windows']:>4}/{r['total_windows']}  {chg_str:>8}  {r['price_slope']:>10.6f}  {r['hit_periods']}")

    print("-" * 130)


def _print_anomaly(results):
    """vr_anomaly 策略输出"""
    print("-" * 130)
    print(f"{'排名':>4}  {'代码':<8}  {'综合评分':>8}  {'显性':>4}  {'隐性':>4}  {'最大角度差':>8}  {'涨幅':>8}  {'命中时段'}")
    print("-" * 130)

    for i, r in enumerate(results):
        chg = r['change_pct']
        chg_str = f"+{chg:.2f}%" if chg >= 0 else f"{chg:.2f}%"
        print(f"{i+1:>4}  {r['code']:<8}  {r['score']:>8.4f}  {r['steep_hits']:>4}  {r['turn_hits']:>4}  "
              f"{r['max_angle_diff']:>7.1f}°  {chg_str:>8}  {r['hit_periods']}")

    print("-" * 130)


def export_results(results, strategy_id, date):
    """导出结果到CSV"""
    if not results:
        print("无命中结果，不导出")
        return

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    output_file = os.path.join(data_dir, f"{strategy_id}_{date}.csv")

    # 重命名列并指定顺序
    if strategy_id == 'vr_anomaly':
        col_order = ['代码', '涨幅%', '显性命中', '隐性命中', '最大角度差', '综合评分', '命中窗口', '总窗口', '价格斜率', '命中时段', '日期']
        rename_map = {
            'score': '综合评分',
            'steep_hits': '显性命中',
            'turn_hits': '隐性命中',
            'max_angle_diff': '最大角度差',
            'hit_windows': '命中窗口',
            'total_windows': '总窗口',
            'price_slope': '价格斜率',
            'hit_periods': '命中时段',
            'code': '代码',
            'date': '日期',
            'change_pct': '涨幅%',
        }
    else:
        col_order = ['代码', '涨幅%', '量比斜率(度)', '综合评分', '命中窗口', '总窗口', '价格斜率', '命中时段', '日期']
        rename_map = {
            'score': '综合评分',
            'avg_vr_slope_deg': '量比斜率(度)',
            'hit_windows': '命中窗口',
            'total_windows': '总窗口',
            'price_slope': '价格斜率',
            'hit_periods': '命中时段',
            'code': '代码',
            'date': '日期',
            'change_pct': '涨幅%',
        }
    df = pd.DataFrame(results)
    df = df.rename(columns=rename_map)
    df = df[col_order]
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"已导出: {output_file}")


def export_codes(results, strategy_id, date):
    """导出命中个股代码到文件"""
    if not results:
        print("无命中结果，不导出代码")
        return

    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_file = os.path.join(output_dir, f"{strategy_id}_{date}.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        for r in results:
            f.write(r['code'] + '\n')
    print(f"已导出代码: {output_file} ({len(results)}只)")
