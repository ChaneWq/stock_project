"""
日内超短回测 CLI 入口

用法示例：
    # 单股
    python -m app.backtest.intraday_overnight.main --code 000059 --flag-date 2026-09-01 --sell close
    python -m app.backtest.intraday_overnight.main --code 000059 --flag-date 2026-09-01 --sell open,close,vr --vr 2.5

    # 批量（CSV: trade_date,code）
    python -m app.backtest.intraday_overnight.main --csv batch.csv --sell open,custom1 --take-profit 3 --out result.csv
    python -m app.backtest.intraday_overnight.main --csv batch.csv --sell conditional --take-profit 3 --workers 4

作者：PyStock项目组
日期：2026-09-06
版本：1.1.0
"""

import argparse

from .backtest import (
    run_backtest, run_batch, format_results, summarize, BacktestError,
)
from .strategies import STRATEGY_REGISTRY


def main():
    parser = argparse.ArgumentParser(
        description='日内超短回测：flag_date收盘买入，下一交易日按可插拔策略卖出'
                    '（单股 --code 或批量 --csv 二选一）')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--code', help='单股模式：股票代码（6位）')
    group.add_argument('--csv', help='批量模式：CSV路径（列: trade_date,code）')
    parser.add_argument('--flag-date', help='单股模式：买入日期 YYYY-MM-DD（收盘价买入）')
    parser.add_argument('--sell', default='close',
                        help=f"卖出策略，逗号分隔可多选对比，可选: {list(STRATEGY_REGISTRY)}")
    parser.add_argument('--time', default='10:00', help='fixed_time 策略卖出时刻，默认10:00')
    parser.add_argument('--take-profit', type=float, default=None,
                        help='conditional/custom1 策略止盈涨幅%%，如 3 表示+3%%')
    parser.add_argument('--stop-loss', type=float, default=None,
                        help='conditional 策略止损跌幅%%，如 -2 表示-2%%')
    parser.add_argument('--fallback', default='14:57',
                        help='conditional/vr 策略兜底时刻，默认14:57')
    parser.add_argument('--vr', type=float, default=2.5, help='vr 策略量比阈值，默认2.5')
    parser.add_argument('--offset', type=int, default=300,
                        help='日线拉取条数（flag_date 较久远时调大）')
    parser.add_argument('--out', default='batch_result.csv',
                        help='批量模式：明细结果CSV输出路径，默认 batch_result.csv')
    parser.add_argument('--workers', type=int, default=1,
                        help='批量模式：并行线程数，默认1串行')
    args = parser.parse_args()

    sell_names = [s.strip() for s in args.sell.split(',') if s.strip()]
    params = {
        'time': args.time,
        'take_profit': args.take_profit,
        'stop_loss': args.stop_loss,
        'fallback': args.fallback,
        'vr': args.vr,
    }

    try:
        if args.csv:
            detail = run_batch(args.csv, sell_names, params,
                               offset=args.offset, out_path=args.out,
                               workers=args.workers)
            print(summarize(detail))
        else:
            if not args.flag_date:
                parser.error('单股模式需要 --flag-date')
            results = run_backtest(args.code, args.flag_date, sell_names,
                                   params, args.offset)
            print(format_results(results))
    except BacktestError as e:
        print(f"❌ 回测失败: {e}")


if __name__ == '__main__':
    main()
