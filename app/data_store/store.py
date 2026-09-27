"""
日线数据读写核心

接口输出与数据层 BasicBars.get_daily 完全一致
（列名 / 排序最新在前 / trade_date 格式 YYYY-MM-DD）：

    save_daily(df)                批量写入（INSERT OR REPLACE，幂等）
    load_daily(code, start, end)  纯本地读取
    get_daily(code, start, end)   对外主接口：本地缺 → 透传网络取数并回写
    get_latest_date(code)         同步水位（本地最新 trade_date）

用法：
    >>> from app.data_store import get_daily
    >>> df = get_daily('000001', start='2026-01-01')
"""

import time
import threading
from datetime import datetime

import pandas as pd

from pystock_data import BasicBars

from .config import DEFAULT_BACKFILL_DAYS, FALLBACK_TTL
from .db import get_conn, write_conn

# 标准列顺序（与数据层一致）
_COLUMNS = ['stock_code', 'datetime', 'trade_date',
            'open', 'close', 'high', 'low', 'volume', 'amount']

# 透传回源限频记录 {code: 上次回源时间戳}
_fallback_ts = {}
_fallback_lock = threading.Lock()

# BasicBars 实例复用（工程惯例同指标类；避免每次回源重建连接与服务器探测的秒级开销）
# 配合下方 _fetch_lock 串行使用，单 client 无并发冲突
_basic_bars = BasicBars()

# 回源串行锁：多线程（预取/并发请求）下回源排队执行，天然限速防封禁
_fetch_lock = threading.Lock()


def save_daily(df: pd.DataFrame) -> int:
    """
    批量写入日线（幂等，重复执行安全）

    Args:
        df (DataFrame): 数据层标准格式（须含 stock_code / datetime / trade_date 列），
                        多只股票混在一个 df 也可

    Returns:
        int: 写入行数

    Example:
        >>> df = BasicBars().get_daily('000001', 100)
        >>> n = save_daily(df)
    """
    if df is None or df.empty:
        return 0

    required = {'stock_code', 'datetime', 'trade_date',
                'open', 'close', 'high', 'low', 'volume', 'amount'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"save_daily 缺少必需列: {sorted(missing)}")

    sql = """
        INSERT OR REPLACE INTO daily_bars
        (code, trade_date, dt, open, high, low, close, volume, amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    total = 0
    for code, g in df.groupby('stock_code'):
        rows = [
            (code, str(r.trade_date), str(r.datetime),
             r.open, r.high, r.low, r.close, r.volume, r.amount)
            for r in g[['trade_date', 'datetime', 'open', 'high', 'low',
                        'close', 'volume', 'amount']].itertuples(index=False)
        ]
        with write_conn() as conn:
            conn.executemany(sql, rows)
        total += len(rows)
    return total


def load_daily(code: str, start: str = None, end: str = None) -> pd.DataFrame:
    """
    纯本地读取日线（不触网络）

    Args:
        code (str): 6位股票代码
        start (str, optional): 起始日期 YYYY-MM-DD（含）
        end (str, optional): 截止日期 YYYY-MM-DD（含）

    Returns:
        DataFrame: 标准列、最新在前；本地无数据时返回空 DataFrame（带列名）
    """
    sql = ("SELECT trade_date, dt, open, high, low, close, volume, amount "
           "FROM daily_bars WHERE code = ?")
    params = [code]
    if start:
        sql += " AND trade_date >= ?"
        params.append(start)
    if end:
        sql += " AND trade_date <= ?"
        params.append(end)
    sql += " ORDER BY trade_date DESC"

    conn = get_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()

    if not rows:
        return pd.DataFrame(columns=_COLUMNS)

    df = pd.DataFrame(rows, columns=['trade_date', 'dt',
                                     'open', 'high', 'low', 'close',
                                     'volume', 'amount'])
    df.insert(0, 'stock_code', code)
    df.insert(1, 'datetime', pd.to_datetime(df.pop('dt')))
    return df[_COLUMNS].reset_index(drop=True)


def get_latest_date(code: str):
    """
    查本地水位（该股最新 trade_date）

    Returns:
        str: YYYY-MM-DD；本地无该股时返回 None
    """
    conn = get_conn()
    try:
        row = conn.execute(
            "SELECT MAX(trade_date) FROM daily_bars WHERE code = ?", [code]
        ).fetchone()
    finally:
        conn.close()
    return row[0] if row and row[0] else None


def get_daily(code: str, start: str = None, end: str = None) -> pd.DataFrame:
    """
    读取日线（透传+回写模式）：

    1. 请求范围被本地完全覆盖 → 直接返回（毫秒级）
    2. 本地无该股 / 请求末端超出本地水位 → 自动走网络补齐并回写

    Args:
        code (str): 6位股票代码
        start (str, optional): 起始日期 YYYY-MM-DD（含）
        end (str, optional): 截止日期 YYYY-MM-DD（含），缺省为今天

    注意：
        - 回源深度按请求范围自动估算（start 较早会自动深回补）
        - 同一股票回源限频 FALLBACK_TTL 秒（停牌/非交易日不反复回源）；
          仅回源成功才占用限频窗口，失败/空响应立即释放可重试
    """
    code = (code or '').strip()
    needed_end = end or datetime.now().strftime('%Y-%m-%d')
    latest = get_latest_date(code)

    # 需要回源：本地无数据，或请求末端超出本地水位
    if (latest is None or latest < needed_end) and _allow_fallback(code):
        try:
            with _fetch_lock:
                # 双检：排队等锁期间数据可能已被其它请求回源完成
                latest_in_lock = get_latest_date(code)
                if latest_in_lock is not None and latest_in_lock >= needed_end:
                    return load_daily(code, start, end)
                offset = _estimate_offset(start, latest)
                df = _basic_bars.get_daily(code, offset)
                saved = save_daily(df)
        except Exception:
            _release_fallback(code)
            raise
        if saved == 0:
            # 空响应不占用限频窗口：下次请求立即可重试
            _release_fallback(code)

    return load_daily(code, start, end)


def _estimate_offset(start: str, latest: str) -> int:
    """
    估算回源需要的 bar 数量

    取 start / 水位中更早者到今天的工作日数（≈交易日数）+ 缓冲
    """
    bases = [pd.Timestamp(x) for x in (start, latest) if x]
    if not bases:
        return DEFAULT_BACKFILL_DAYS
    base = min(bases)
    bd = pd.bdate_range(base, pd.Timestamp.today().normalize())
    return max(30, len(bd) + 15)


def _allow_fallback(code: str) -> bool:
    """透传回源限频：同一股票 FALLBACK_TTL 秒内只回源一次"""
    now = time.time()
    with _fallback_lock:
        if now - _fallback_ts.get(code, 0) < FALLBACK_TTL:
            return False
        _fallback_ts[code] = now
        return True


def _release_fallback(code: str) -> None:
    """回源失败/空响应时释放限频窗口，下次请求可立即重试"""
    with _fallback_lock:
        _fallback_ts.pop(code, None)
