"""
日内超短回测 CLI 入口

用法示例：
    python -m app.backtest.intraday_overnight.main --code 000059 --flag-date 2026-09-01 --sell close
    python -m app.backtest.intraday_overnight.main --code 000059 --flag-date 2026-09-01 --sell open,close,vr --vr 2.5
    python -m app.backtest.intraday_overnight.main --code 000059 --flag-date 2026-09-01 --sell conditional --take-profit 3 --stop-loss -2

作者：PyStock项目组
日期：2026-09-05
版本：1.0.0
"""

import argparse

from .backtest import run_backtest, format_results, BacktestError
from .strategies import STRATEGY_REGISTRY


def main():
    parser = argparse.ArgumentParser(
        description='日内超短回测：flag_date收盘买入，下一交易日按可插拔策略卖出')
    parser.add_argument('--code', required=True, help='股票代码（6位）')
    parser.add_argument('--flag-date', required=True, help='买入日期 YYYY-MM-DD（收盘价买入）')
    parser.add_argument('--sell', default='close',
                        help=f"卖出策略，逗号分隔可多选对比，可选: {list(STRATEGY_REGISTRY)}")
    parser.add_argument('--time', default='10:00', help='fixed_time 策略卖出时刻，默认10:00')
    parser.add_argument('--take-profit', type=float, default=None,
                        help='conditional 策略止盈涨幅%%，如 3 表示+3%%')
    parser.add_argument('--stop-loss', type=float, default=None,
                        help='conditional 策略止损跌幅%%，如 -2 表示-2%%')
    parser.add_argument('--fallback', default='14:57',
                        help='conditional/vr 策略兜底时刻，默认14:57')
    parser.add_argument('--vr', type=float, default=2.5, help='vr 策略量比阈值，默认2.5')
    parser.add_argument('--offset', type=int, default=300,
                        help='日线拉取条数（flag_date 较久远时调大）')
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
        results = run_backtest(args.code, args.flag_date, sell_names, params, args.offset)
        print(format_results(results))
    except BacktestError as e:
        print(f"❌ 回测失败: {e}")


if __name__ == '__main__':
    main()
