"""
增量同步

流程（每只股票）：
    1. 查本地水位 MAX(trade_date)
    2. 无记录 → 按回补深度全量拉取（days / DEFAULT_BACKFILL_DAYS）
    3. 有记录 → 按水位到今天的工作日数估算 offset，只补缺失
    4. 批量写入（INSERT OR REPLACE 幂等，顺带修正服务端修订的历史数据）
    5. 每 BATCH_SIZE 只间隔 BATCH_INTERVAL 秒（防封禁）
"""

import time
from datetime import datetime

import pandas as pd

from pystock_data import BasicBars

from .config import BATCH_SIZE, BATCH_INTERVAL, DEFAULT_BACKFILL_DAYS
from .store import save_daily, get_latest_date


def sync_daily(codes, days: int = None, log=print):
    """
    增量同步一批股票的日线

    Args:
        codes (list[str]): 6位股票代码列表
        days (int, optional): 首次回补深度（交易日数），缺省用 DEFAULT_BACKFILL_DAYS
        log (callable): 日志函数，缺省 print

    Returns:
        list[dict]: 逐股结果
            {code, status: 'synced'|'latest'|'error', fetched, new, latest}
            - synced : 本次有拉取并写入（new 为新增行数，不含覆盖旧数据）
            - latest : 本地已是最新，本次跳过
            - error  : 失败（error 字段为原因）
    """
    source = BasicBars()
    today = datetime.now().strftime('%Y-%m-%d')
    results = []

    for i, code in enumerate(codes):
        code = (code or '').strip()
        if not code:
            continue
        try:
            latest = get_latest_date(code)
            if latest is None:
                # 无本地数据 → 全量回补
                offset = days or DEFAULT_BACKFILL_DAYS
            else:
                # 有水位 → 按缺口估算拉取量
                gap = len(pd.bdate_range(latest, pd.Timestamp(today))) - 1
                if gap <= 0:
                    results.append({'code': code, 'status': 'latest',
                                    'fetched': 0, 'new': 0, 'latest': latest})
                    log(f"[{i+1}/{len(codes)}] {code} 本地已是最新 ({latest})，跳过")
                    continue
                offset = gap + 10

            df = source.get_daily(code, offset)
            if df.empty:
                results.append({'code': code, 'status': 'error',
                                'error': '网络返回空数据',
                                'fetched': 0, 'new': 0, 'latest': latest})
                log(f"[{i+1}/{len(codes)}] {code} 网络返回空数据")
                continue

            # 统计新增（水位之后的行），再整体写入（幂等）
            new = int((df['trade_date'] > latest).sum()) if latest else len(df)
            save_daily(df)
            new_latest = get_latest_date(code)

            results.append({'code': code, 'status': 'synced',
                            'fetched': len(df), 'new': new, 'latest': new_latest})
            log(f"[{i+1}/{len(codes)}] {code} 同步完成："
                f"拉取 {len(df)} 行，新增 {new} 行，最新 {new_latest}")

        except Exception as e:
            results.append({'code': code, 'status': 'error',
                            'error': str(e), 'fetched': 0, 'new': 0})
            log(f"[{i+1}/{len(codes)}] {code} 同步失败: {e}")

        # 批次间隔防封禁
        if (i + 1) % BATCH_SIZE == 0:
            time.sleep(BATCH_INTERVAL)

    return results


def summarize(results):
    """汇总统计"""
    synced = [r for r in results if r['status'] == 'synced']
    latest = [r for r in results if r['status'] == 'latest']
    errors = [r for r in results if r['status'] == 'error']
    return {
        'total': len(results),
        'synced': len(synced),
        'latest': len(latest),
        'error': len(errors),
        'new_rows': sum(r.get('new', 0) for r in synced),
    }
