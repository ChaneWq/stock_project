"""
日内超短回测引擎

功能：
- 主题：flag_date 收盘价买入，下一交易日卖出（卖出条件可插拔）
- 拉取日线 → 定位买卖两日 → 按策略声明拉分时 → 调用策略插件 → 汇总结果
- 支持单股回测（run_backtest）与批量回测（run_batch，CSV 输入）

作者：PyStock项目组
日期：2026-09-06
版本：1.1.0
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd

from pystock_data.source import TdxSource
from pystock_data.basic import BasicMinutesWithVR

from .strategies import STRATEGY_REGISTRY
from .strategies.base import SellContext

# 默认日线拉取条数（覆盖 flag_date 即可）
DEFAULT_BARS_OFFSET = 300


class BacktestError(Exception):
    """回测输入/数据错误（用户可见）"""


def _normalize_date(date_str: str) -> str:
    """日期归一化：兼容 'YYYY-MM-DD' / 'YYYYMMDD'，统一返回 'YYYY-MM-DD'"""
    s = str(date_str).strip()
    if '-' in s:
        parts = s.split('-')
        if len(parts) != 3:
            raise BacktestError(f"日期格式无法识别: {date_str}")
        return f"{parts[0]}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    if len(s) == 8 and s.isdigit():
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    raise BacktestError(f"日期格式无法识别: {date_str}")


def execute_one(code: str, flag_date: str, sell_names: list,
                params: dict = None, daily_df: pd.DataFrame = None,
                source: TdxSource = None,
                offset: int = DEFAULT_BARS_OFFSET) -> list:
    """
    执行单次回测（一次买入，多个卖出策略对比）

    与 run_backtest 的区别：日线数据与数据源可由外部注入
    （批量场景下同一 code 的日线跨行复用、多线程共享数据源）

    Args:
        code (str): 股票代码（6位字符串）
        flag_date (str): 买入日期（当日收盘价买入，内部自动归一化）
        sell_names (list): 卖出策略名列表（见 strategies/STRATEGY_REGISTRY）
        params (dict, optional): 策略参数（透传给各策略，如 time/take_profit/vr）
        daily_df (DataFrame, optional): 已拉取的日线（标准列，含 trade_date/close 等）；
            None 则自行拉取
        source (TdxSource, optional): 数据源实例；None 则新建
        offset (int): daily_df 未提供时的日线拉取条数

    Returns:
        list[dict]: 每个策略一条结果记录

    Raises:
        BacktestError: flag_date 非交易日 / 超出范围 / 无下一交易日 / 分时缺失等
    """
    params = params or {}
    flag_date = _normalize_date(flag_date)

    # ---- 校验策略名 ----
    unknown = [n for n in sell_names if n not in STRATEGY_REGISTRY]
    if unknown:
        raise BacktestError(
            f"未知卖出策略: {unknown}，可选: {list(STRATEGY_REGISTRY)}")

    # ---- 日线定位 ----
    if source is None:
        source = TdxSource()
    if daily_df is None:
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
        vr = BasicMinutesWithVR(source=source)
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


def run_backtest(code: str, flag_date: str, sell_names: list,
                 params: dict = None, offset: int = DEFAULT_BARS_OFFSET) -> list:
    """
    执行单股回测：一次买入，多个卖出策略对比

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
    source = TdxSource()
    daily_df = source.fetch_bars(code, 9, offset)
    return execute_one(code, flag_date, sell_names, params,
                       daily_df=daily_df, source=source)


def _read_batch_csv(csv_path: str) -> pd.DataFrame:
    """
    读取批量回测 CSV（列: trade_date, code）

    Returns:
        DataFrame: [trade_date, code]，code 为字符串（保留前导零），日期已归一化
    """
    try:
        df = pd.read_csv(csv_path, dtype={'code': str})
    except FileNotFoundError:
        raise BacktestError(f"CSV 文件不存在: {csv_path}")
    except Exception as e:
        raise BacktestError(f"CSV 读取失败: {e}")

    cols = [c.strip().lower() for c in df.columns]
    if 'trade_date' not in cols or 'code' not in cols:
        raise BacktestError(f"CSV 必须包含 trade_date 和 code 两列，实际列: {df.columns.tolist()}")

    rename = dict(zip(df.columns, cols))
    df = df.rename(columns=rename)[['trade_date', 'code']].copy()
    df['code'] = df['code'].astype(str).str.strip()
    df['trade_date'] = df['trade_date'].apply(lambda x: _normalize_date(x))
    return df


def _fetch_daily_cached(code: str, source: TdxSource,
                        offset: int) -> pd.DataFrame:
    """预取线程：拉取单只股票日线，失败返回 None（执行阶段再报错）"""
    try:
        return source.fetch_bars(code, 9, offset)
    except Exception:
        return None


def run_batch(csv_path: str, sell_names: list, params: dict = None,
              offset: int = DEFAULT_BARS_OFFSET, out_path: str = None,
              workers: int = 1) -> pd.DataFrame:
    """
    批量回测：CSV（trade_date, code）逐行执行"收盘买、次日卖"

    性能：按 code 分组预取日线（同 code 多行共享一次拉取）；
    workers>1 时多线程执行（数据源线程安全模式）

    Args:
        csv_path (str): 输入 CSV 路径（列: trade_date, code）
        sell_names (list): 卖出策略名列表
        params (dict, optional): 策略参数（透传）
        offset (int): 日线拉取条数
        out_path (str, optional): 明细结果输出 CSV 路径；None 不落盘
        workers (int): 并行线程数，默认 1（串行）

    Returns:
        DataFrame: 明细结果（每行 = CSV 一行 × 一个策略；失败行 error 列非空）
    """
    params = params or {}

    # ---- 校验策略名（提前失败，不浪费网络请求）----
    unknown = [n for n in sell_names if n not in STRATEGY_REGISTRY]
    if unknown:
        raise BacktestError(
            f"未知卖出策略: {unknown}，可选: {list(STRATEGY_REGISTRY)}")

    rows = _read_batch_csv(csv_path)
    if rows.empty:
        raise BacktestError("CSV 无有效数据行")
    print(f"批量回测: {len(rows)} 行 | 策略: {sell_names} | 线程: {workers}")

    # ---- 按 code 分组预取日线（同 code 共享一次拉取）----
    codes = rows['code'].unique().tolist()
    daily_cache = {}
    fetch_workers = max(1, min(workers, len(codes)))
    source = TdxSource(thread_safe=True)
    if fetch_workers == 1:
        for i, c in enumerate(codes, 1):
            daily_cache[c] = _fetch_daily_cached(c, source, offset)
            if i % 50 == 0 or i == len(codes):
                print(f"日线预取: {i}/{len(codes)}")
    else:
        with ThreadPoolExecutor(max_workers=fetch_workers) as pool:
            futures = {pool.submit(_fetch_daily_cached, c, source, offset): c
                       for c in codes}
            done = 0
            for fut in as_completed(futures):
                c = futures[fut]
                daily_cache[c] = fut.result()
                done += 1
                if done % 50 == 0 or done == len(codes):
                    print(f"日线预取: {done}/{len(codes)}")

    # ---- 逐行执行 ----
    def _one(row) -> list:
        code = row['code']
        try:
            return execute_one(code, row['trade_date'], sell_names, params,
                               daily_df=daily_cache.get(code), source=source)
        except Exception as e:
            return [{'code': code, 'buy_date': row['trade_date'],
                     'strategy': '-', 'error': str(e)}]

    results = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = [pool.submit(_one, row) for _, row in rows.iterrows()]
        for done, fut in enumerate(as_completed(futures), 1):
            results.extend(fut.result())
            if done % 20 == 0 or done == len(futures):
                print(f"回测进度: {done}/{len(futures)}")

    detail = pd.DataFrame(results)
    col_order = ['code', 'buy_date', 'sell_date', 'buy_price', 'strategy',
                 'sell_price', 'sell_time', 'pct', 'max_gain_pct',
                 'max_loss_pct', 'reason', 'error']
    for c in col_order:
        if c not in detail.columns:
            detail[c] = None
    detail = detail[col_order].sort_values(
        ['code', 'buy_date', 'strategy']).reset_index(drop=True)

    if out_path:
        detail.to_csv(out_path, index=False, encoding='utf-8-sig')
        print(f"明细已保存: {out_path}")

    return detail


def summarize(detail: pd.DataFrame) -> str:
    """
    按策略汇总统计（仅成功行）

    Returns:
        str: 汇总表文本（样本数/胜率/平均收益/最佳/最差）
    """
    ok = detail[(detail['error'].isna()) & (detail['strategy'] != '-')]
    if ok.empty:
        return "无成功回测记录"

    lines = [
        "",
        "按策略汇总（成功行）",
        "-" * 78,
        f"{'策略':<12}{'样本数':>6}{'胜率':>8}{'平均收益%':>10}{'最佳%':>9}{'最差%':>9}",
        "-" * 78,
    ]
    for name, g in ok.groupby('strategy'):
        win_rate = (g['pct'] > 0).mean() * 100
        lines.append(
            f"{name:<12}{len(g):>6}{win_rate:>7.1f}%{g['pct'].mean():>+10.2f}"
            f"{g['pct'].max():>+9.2f}{g['pct'].min():>+9.2f}")
    return '\n'.join(lines)


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
