"""
本地数据落地 CLI

用法（项目根目录运行）：

    # 增量同步（codes.txt 每行一个代码）
    python -m app.data_store.main --file app/minute_vr_scanner/codes.txt

    # 指定股票 + 首次回补深度
    python -m app.data_store.main --codes 000001,600519 --days 500

    # 查看本地库存概况
    python -m app.data_store.main --stats
"""

import argparse
import os
import re
import sys

from .db import get_conn
from .sync import sync_daily, summarize

# 合法代码：6位数字
_CODE_RE = re.compile(r'^\d{6}$')


def load_codes(file_path: str):
    """
    从文件加载股票代码清单

    兼容格式：
    - codes.txt：每行一个代码
    - stocks.csv（code,name,remark,category）：逗号分隔取第一列，跳过表头
    """
    codes = []
    with open(file_path, encoding='utf-8-sig') as f:
        for line in f:
            first = line.split(',')[0].strip()
            if _CODE_RE.match(first):
                codes.append(first)
    # 去重保序
    seen = set()
    return [c for c in codes if not (c in seen or seen.add(c))]


def show_stats():
    """打印本地库存概况：每只股票的行数与日期范围"""
    conn = get_conn()
    try:
        rows = conn.execute(
            "SELECT code, COUNT(*), MIN(trade_date), MAX(trade_date) "
            "FROM daily_bars GROUP BY code ORDER BY code"
        ).fetchall()
        total = conn.execute("SELECT COUNT(*) FROM daily_bars").fetchone()[0]
    finally:
        conn.close()

    if not rows:
        print("本地库为空，还没有落地数据")
        return

    print(f"{'代码':<10}{'行数':>8}{'最早':>14}{'最新':>14}")
    print("-" * 46)
    for code, cnt, dmin, dmax in rows:
        print(f"{code:<10}{cnt:>8}{dmin:>14}{dmax:>14}")
    print("-" * 46)
    print(f"共 {len(rows)} 只股票，{total} 行日线数据")


def main():
    parser = argparse.ArgumentParser(description="本地数据落地（SQLite）日线同步工具")
    parser.add_argument('--file', help='股票代码文件路径（每行一个代码，兼容 stocks.csv）')
    parser.add_argument('--codes', help='股票代码，逗号分隔，如 000001,600519')
    parser.add_argument('--days', type=int, default=None,
                        help='首次回补深度（交易日数），默认 300')
    parser.add_argument('--stats', action='store_true', help='查看本地库存概况')
    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    codes = []
    if args.file:
        if not os.path.exists(args.file):
            print(f"文件不存在: {args.file}")
            sys.exit(1)
        codes = load_codes(args.file)
    if args.codes:
        codes += [c.strip() for c in args.codes.split(',') if _CODE_RE.match(c.strip())]

    if not codes:
        parser.print_help()
        print("\n错误：请通过 --file 或 --codes 指定股票代码")
        sys.exit(1)

    print(f"开始增量同步 {len(codes)} 只股票（首次回补 {args.days or 300} 个交易日）\n")
    results = sync_daily(codes, days=args.days)

    # 汇总
    s = summarize(results)
    print("\n" + "=" * 40)
    print(f"同步完成：共 {s['total']} 只 "
          f"（写入 {s['synced']}，已最新 {s['latest']}，失败 {s['error']}）"
          f"，新增 {s['new_rows']} 行")

    if s['error']:
        print("\n失败明细：")
        for r in results:
            if r['status'] == 'error':
                print(f"  {r['code']}: {r.get('error')}")
        sys.exit(2)


if __name__ == '__main__':
    main()
