"""
日内超短回测引擎

功能：
- 主题：flag_date 收盘价买入，下一交易日卖出（卖出条件可插拔）
- 拉取日线 → 定位买卖两日 → 按策略声明拉分时 → 调用策略插件 → 汇总结果

作者：PyStock项目组
日期：2026-09-05
版本：1.0.0
"""

import pandas as pd

from pystock_data.source import TdxSource
from pystock_data.basic import BasicMinutesWithVR

from .strategies import STRATEGY_REGISTRY
from .strategies.base import SellContext

# 默认日线拉取条数（覆盖 flag_date 即可）
DEFAULT_BARS_OFFSET = 300


class BacktestError(Exception):
    """回测输入/数据错误（用户可见）"""


def run_backtest(code: str, flag_date: str, sell_names: list,
                 params: dict = None, offset: int = DEFAULT_BARS_OFFSET) -> list:
    """
    执行回测：一次买入，多个卖出策略对比

    Args:
        code (str): 股票代码（6位字符串）
        flag_date (str): 买入日期 'YYYY-MM-DD'（当日收盘价买入）
        sell_names (list): 卖出策略名列表（见 strategies/STRATEGY_REGISTRY）
        params (dict, optional): 策略参数（透传给各策略，如 time/take_profit/vr）
        offset (int): 日线拉取条数，默认300

    Returns:
        list[dict]: 每个策略一条结果记录

    Raises:
        BacktestError: flag_date 非交易日 / 超出范围 / 无下一交易日等
    """
    params = params or {}

    # ---- 校验策略名 ----
    unknown = [n for n in sell_names if n not in STRATEGY_REGISTRY]
    if unknown:
        raise BacktestError(
            f"未知卖出策略: {unknown}，可选: {list(STRATEGY_REGISTRY)}")

    # ---- 拉日线并定位 ----
    source = TdxSource()
    daily_df = source.fetch_bars(code, 9, offset)
    if daily_df is None or daily_df.empty:
        raise BacktestError(f"未获取到 {code} 日线数据")

    dates = daily_df['trade_date'].astype(str).tolist()
    if flag_date not in dates:
        raise BacktestError(
            f"{flag_date} 不是 {code} 的交易日（或超出最近{offset}根K线范围）")

    idx = dates.index(flag_date)
    if idx == len(dates) - 1:
        raise BacktestError(f"{flag_date} 是最新交易日，下一交易日尚未到来，无法回测")

    buy_row = daily_df.iloc[idx]
    sell_row = daily_df.iloc[idx + 1]
    sell_date = dates[idx + 1]
    buy_price = float(buy_row['close'])

    # ---- 拉取卖出日分时（策略用 + 浮盈浮亏统一按 9:30~收盘 分时口径）----
    need_plain = any(STRATEGY_REGISTRY[n].needs_minutes for n in sell_names)
    need_vr = any(STRATEGY_REGISTRY[n].needs_vr for n in sell_names)
    date_compact = sell_date.replace('-', '')

    minute_df = None
    if need_vr:
        vr = BasicMinutesWithVR()
        minute_df = vr.get_data(code, date_compact, n=5)
        if minute_df is None or minute_df.empty:
            raise BacktestError(f"未获取到 {code} 在 {sell_date} 的分时量比数据")
    elif need_plain:
        minute_df = source.fetch_minutes(code, date_compact)
        if minute_df is None or minute_df.empty:
            raise BacktestError(f"未获取到 {code} 在 {sell_date} 的分时数据")
    else:
        # 纯日线策略也拉一次分时：最大浮盈/浮亏统一用 9:30~收盘 口径（不含竞价）
        minute_df = source.fetch_minutes(code, date_compact)

    # 卖出日盘中最高/最低（9:30~收盘 分时口径；分时缺失时为 None）
    if minute_df is not None and not minute_df.empty:
        session_high = float(minute_df['high'].max())
        session_low = float(minute_df['low'].min())
    else:
        session_high = session_low = None

    # ---- 逐策略执行 ----
    results = []
    for name in sell_names:
        strategy = STRATEGY_REGISTRY[name]
        ctx = SellContext(
            code=code,
            buy_price=buy_price,
            buy_date=flag_date,
            sell_date=sell_date,
            sell_day_row=sell_row,
            minute_df=minute_df,
            params=params,
        )
        r = strategy.determine_sell(ctx)

        pct = (r.sell_price / buy_price - 1) * 100
        # 盘中最大浮盈/浮亏（相对买入价，9:30~收盘 分时口径，不含竞价）
        max_gain = ((session_high / buy_price - 1) * 100
                    if session_high is not None else None)
        max_loss = ((session_low / buy_price - 1) * 100
                    if session_low is not None else None)

        results.append({
            'code': code,
            'buy_date': flag_date,
            'buy_price': buy_price,
            'sell_date': sell_date,
            'strategy': name,
            'sell_price': round(r.sell_price, 3),
            'sell_time': r.sell_time,
            'pct': round(pct, 2),
            'max_gain_pct': round(max_gain, 2) if max_gain is not None else None,
            'max_loss_pct': round(max_loss, 2) if max_loss is not None else None,
            'reason': r.reason,
        })

    return results


def format_results(results: list) -> str:
    """
    格式化回测结果为对比表文本

    Args:
        results (list[dict]): run_backtest 输出

    Returns:
        str: 多行文本（表头 + 每策略一行）
    """
    first = results[0]
    lines = [
        f"股票: {first['code']} | 买入: {first['buy_date']} 收盘 {first['buy_price']}"
        f" | 卖出日: {first['sell_date']}",
        "-" * 100,
        f"{'策略':<12}{'卖出价':>10}{'时刻':>8}{'收益%':>8}"
        f"{'最大浮盈%':>10}{'最大浮亏%':>10}  原因",
        "-" * 100,
    ]
    for r in results:
        gain_s = f"{r['max_gain_pct']:+.2f}" if r['max_gain_pct'] is not None else '-'
        loss_s = f"{r['max_loss_pct']:+.2f}" if r['max_loss_pct'] is not None else '-'
        lines.append(
            f"{r['strategy']:<12}{r['sell_price']:>10}{r['sell_time']:>8}"
            f"{r['pct']:>+8}{gain_s:>10}{loss_s:>10}  {r['reason']}"
        )
    return '\n'.join(lines)
