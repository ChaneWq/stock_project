"""
股票特征数据入库入口

功能：
- 指定日期区间，全市场股票拉日线 → 计算指标特征 → 提取分钟量比特征 → 写入 DorisDB
- 多线程并发，线程独立数据源（thread_safe=True）
- 支持 dry-run（只算不写）与小批量验证（limit）

用法：
    python app/database/feature_import/main.py --dry-run --limit 5   # 直接运行（含sys.path引导）
    python -m app.database.feature_import.main --start 2026-08-25 --end 2026-08-29  # 模块方式

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import os
import sys

# sys.path 引导：支持任意位置直接运行本文件（python main.py）
# 上跳4级：feature_import → database → app → 项目根
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import argparse
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import pandas as pd

from pystock_data.source import TdxSource

# 直接运行（非 -m 模块方式）时，包内相对导入转为绝对导入
if __package__ is None or __package__ == '':
    _PKG_DIR = os.path.dirname(os.path.abspath(__file__))
    if _PKG_DIR not in sys.path:
        sys.path.insert(0, _PKG_DIR)
    from config import CONFIG
    from db_writer import DorisWriter
    from feature_extractor import extract_features
    from minute_feature import MinuteFeatureFetcher, attach_minute_features
else:
    from .config import CONFIG
    from .db_writer import DorisWriter
    from .feature_extractor import extract_features
    from .minute_feature import MinuteFeatureFetcher, attach_minute_features


# ---------------- 线程资源（每线程独立数据源，懒加载） ---------------- #

_local = threading.local()


def _get_thread_resources():
    """获取当前线程的数据源实例（首次调用时创建）"""
    if not hasattr(_local, 'source'):
        _local.source = TdxSource(thread_safe=True)
        _local.minute_fetcher = MinuteFeatureFetcher(thread_safe=True)
    return _local


# ---------------- 单只股票处理 ---------------- #

def process_stock(code: str, start_dt: str, end_dt: str,
                  offset: int, dry_run: bool = False) -> tuple:
    """
    处理单只股票：拉日线 → 算特征 → 附加分钟特征

    Returns:
        tuple: (code, 'OK', features_df) 或 (code, 'ERROR: ...', None)
        features_df 由调用方攒批写库（写库模式）；dry-run 时为 None
    """
    try:
        res = _get_thread_resources()

        # 日线数据（fetch_bars 返回标准列：trade_date/open/close/high/low/volume/amount）
        daily_df = res.source.fetch_bars(code, 9, offset)
        if daily_df is None or daily_df.empty:
            return (code, 'ERROR: 日线数据为空', None)

        # 日线指标特征 + 分钟量比特征（传日线数据复用基准量，省网络请求）
        features = extract_features(code, daily_df, start_dt, end_dt)
        if features.empty:
            return (code, 'ERROR: 日期窗口内无数据', None)
        features = attach_minute_features(features, res.minute_fetcher, daily_df)

        if dry_run:
            return (code, 'OK', None)

        return (code, 'OK', features)

    except Exception as e:
        return (code, f'ERROR: {e}', None)


# ---------------- 股票清单 ---------------- #

def get_all_codes(writer: DorisWriter, stock_list_table: str) -> list:
    """从 DorisDB 股票清单表获取全部股票代码"""
    return writer.query_codes(f'SELECT code FROM {stock_list_table};')


# ---------------- 主流程 ---------------- #

def run(start_dt: str = None, end_dt: str = None, dry_run: bool = False,
        limit: int = None) -> None:
    """
    执行特征导入

    Args:
        start_dt (str, optional): 起始日期 'YYYY-MM-DD'，默认 N 天前（见配置）
        end_dt (str, optional): 结束日期，默认今天
        dry_run (bool, optional): 只计算不写库
        limit (int, optional): 只处理前 N 只股票（验证用）
    """
    conf = CONFIG['import']
    if end_dt is None:
        end_dt = datetime.now().strftime('%Y-%m-%d')
    if start_dt is None:
        start_dt = (datetime.now() - timedelta(days=conf['date_window_days'])).strftime('%Y-%m-%d')

    writer = DorisWriter(CONFIG['db'], conf['table_name'])
    codes = get_all_codes(writer, conf['stock_list_table'])
    if limit:
        codes = codes[:limit]

    print(f"日期窗口: {start_dt} ~ {end_dt} | 模式: {'dry-run' if dry_run else '写库'}")
    print(f"共 {len(codes)} 只股票，启动 {conf['max_workers']} 线程")

    success, fail = [], []
    pending, pending_codes = [], []   # 攒批缓冲（批量写库）
    BATCH_SIZE = 200
    start_time = time.time()

    def flush_batch():
        """批量写入缓冲区数据"""
        if not pending:
            return
        writer.write(pd.concat(pending, ignore_index=True))
        pending.clear()
        pending_codes.clear()

    with ThreadPoolExecutor(max_workers=conf['max_workers']) as executor:
        futures = {
            executor.submit(process_stock, code, start_dt, end_dt,
                            conf['bars_offset'], dry_run): code
            for code in codes
        }
        for future in as_completed(futures):
            code, msg, features = future.result()
            if msg == 'OK':
                success.append(code)
                print(f"✔ {code} 完成")
                # 攒批写库（主线程单点写入，避免并发写冲突）
                if features is not None:
                    pending.append(features)
                    pending_codes.append(code)
                    if len(pending) >= BATCH_SIZE:
                        flush_batch()
            else:
                fail.append(code)
                print(f"❌ {code} 失败：{msg}")

        # 写入剩余批次
        flush_batch()

    elapsed = time.time() - start_time
    print("\n========== 运行完成 ==========")
    print(f"成功: {len(success)} | 失败: {len(fail)} | 耗时: {elapsed:.1f}s")
    if fail:
        print(f"失败股票({len(fail)}): {fail[:20]}{'...' if len(fail) > 20 else ''}")


def main():
    parser = argparse.ArgumentParser(description='股票特征数据入库')
    parser.add_argument('--start', help='起始日期 YYYY-MM-DD（默认配置的天数窗口）')
    parser.add_argument('--end', help='结束日期 YYYY-MM-DD（默认今天）')
    parser.add_argument('--dry-run', action='store_true', help='只计算不写库')
    parser.add_argument('--limit', type=int, help='只处理前N只股票（验证用）')
    args = parser.parse_args()

    run(start_dt=args.start, end_dt=args.end, dry_run=args.dry_run, limit=args.limit)


if __name__ == '__main__':
    main()
