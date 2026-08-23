"""
量比策略扫描入口（CLI）

运行方式：
    cd g:\\pystock3\\newproject
    python -m app.minute_vr_scanner.main --file app/minute_vr_scanner/codes.txt --date 20260821

数据源：本地 pystock_data（BasicMinutesWithVR，通达信）
"""

import sys
import os
import argparse

from .scanner import scan, print_results, export_results, export_codes, get_latest_trade_date


def main():
    parser = argparse.ArgumentParser(description="量比策略扫描工具（本地数据版）")

    # 通用参数
    parser.add_argument("--strategy", help="策略: vr_slope / vr_anomaly，默认vr_slope", default="vr_slope")
    parser.add_argument("--file", help="股票代码文件路径，每行一个代码", required=True)
    parser.add_argument("--date", help="日期，格式 YYYYMMDD，默认今天", default="")
    parser.add_argument("--n", help="过去n个交易日，默认5", type=int, default=5)
    parser.add_argument("--csv", help="导出CSV到data目录", action="store_true")
    parser.add_argument("--output", help="导出命中个股代码到output目录", action="store_true")
    parser.add_argument("--until", help="截至时间，格式 HH:MM，模拟盘中该时间点运行，如 --until 10:30", default="")
    parser.add_argument("--no_filter", help="不过滤创业板(300/301)、科创板(688)、北交所(9开头)等", action="store_true", default=False)
    parser.add_argument("--change_min", help="涨幅下限(%%)，默认-100不限", type=float, default=-100)
    parser.add_argument("--change_max", help="涨幅上限(%%)，默认100不限", type=float, default=100)
    parser.add_argument("-p", "--print_codes", help="额外打印命中股票代码", action="store_true")

    # vr_slope 策略参数
    parser.add_argument("--vr_slope_window", help="[vr_slope] 窗口大小（分钟），默认3", type=int, default=3)
    parser.add_argument("--vr_slope", help="[vr_slope] 量比斜率角度阈值（度），默认5度", type=float, default=5)
    parser.add_argument("--no_vr_up", help="[vr_slope] 不要求窗口首尾量比增加", action="store_true", default=False)
    parser.add_argument("--no_vr_slope_price_up", help="[vr_slope] 不要求窗口首尾价格上涨", action="store_true", default=False)
    parser.add_argument("--vr_slope_min_hits", help="[vr_slope] 最少命中窗口数，默认3", type=int, default=3)
    parser.add_argument("--vr_slope_merge_gap", help="[vr_slope] 命中窗口间隔<=此值合并，默认2", type=int, default=2)

    # vr_anomaly 策略参数
    parser.add_argument("--anomaly_window", help="[vr_anomaly] 每段窗口大小（分钟），默认3", type=int, default=3)
    parser.add_argument("--anomaly_steep", help="[vr_anomaly] 显性异动角度阈值（度），默认5", type=float, default=5)
    parser.add_argument("--anomaly_turn", help="[vr_anomaly] 隐性异动角度差阈值（度），默认8", type=float, default=8)
    parser.add_argument("--no_anomaly_price_up", help="[vr_anomaly] 不要求后窗首尾价格不下跌", action="store_true", default=False)
    parser.add_argument("--anomaly_min_hits", help="[vr_anomaly] 最少命中次数，默认1", type=int, default=1)
    parser.add_argument("--anomaly_merge_gap", help="[vr_anomaly] 命中间隔<=此值合并，默认2", type=int, default=2)

    args = parser.parse_args()

    # 解析截至时间
    until_hour = None
    until_minute = None
    if args.until:
        try:
            parts = args.until.split(':')
            until_hour = int(parts[0])
            until_minute = int(parts[1])
        except (ValueError, IndexError):
            print("截至时间格式错误，应为 HH:MM，如 10:30")
            sys.exit(1)

    # 读取股票列表
    if not os.path.exists(args.file):
        print("文件不存在: %s" % args.file)
        sys.exit(1)

    with open(args.file, 'r', encoding='utf-8-sig') as f:
        codes = [line.strip() for line in f if line.strip()]

    if not codes:
        print("股票列表为空")
        sys.exit(1)

    # 日期：未指定时用日线最新trade_date（自动处理非交易日运行），全部失败回退今天
    date = args.date or get_latest_trade_date(codes)
    if not args.date:
        print("未指定日期，使用最新交易日: %s" % date)

    # 过滤创业板/科创板/北交所
    if not args.no_filter:
        filter_prefixes = ('300', '301', '688', '9')
        original_count = len(codes)
        codes = [c for c in codes if not c.startswith(filter_prefixes)]
        filtered_count = original_count - len(codes)
        if filtered_count > 0:
            print("已过滤 %d 只（创业板/科创板/北交所），剩余 %d 只" % (filtered_count, len(codes)))

    if not codes:
        print("过滤后股票列表为空")
        sys.exit(1)

    # 构建策略参数
    strategy_id = args.strategy
    if strategy_id == 'vr_slope':
        vr_price_up = not args.no_vr_slope_price_up
        vr_up = not args.no_vr_up
        strategy_kwargs = {
            'window': args.vr_slope_window,
            'vr_slope': args.vr_slope,
            'vr_up': vr_up,
            'price_up': vr_price_up,
            'min_hits': args.vr_slope_min_hits,
            'merge_gap': args.vr_slope_merge_gap,
        }
        print("策略: vr_slope  日期: %s  股票数: %d  窗口: %d分钟  量比斜率: %.0f度  量比增加: %s  价格上涨: %s  最少命中: %d  合并间隔: %d%s" % (
            date, len(codes), args.vr_slope_window, args.vr_slope, vr_up, vr_price_up,
            args.vr_slope_min_hits, args.vr_slope_merge_gap,
            "  截至时间: %s" % args.until if args.until else ""))
    elif strategy_id == 'vr_anomaly':
        anomaly_price_up = not args.no_anomaly_price_up
        strategy_kwargs = {
            'window': args.anomaly_window,
            'steep': args.anomaly_steep,
            'turn': args.anomaly_turn,
            'price_up': anomaly_price_up,
            'min_hits': args.anomaly_min_hits,
            'merge_gap': args.anomaly_merge_gap,
        }
        print("策略: vr_anomaly  日期: %s  股票数: %d  窗口: %d分钟  显性角度: %.0f度  隐性角度差: %.0f度  价格不跌: %s  最少命中: %d  合并间隔: %d%s" % (
            date, len(codes), args.anomaly_window, args.anomaly_steep, args.anomaly_turn, anomaly_price_up,
            args.anomaly_min_hits, args.anomaly_merge_gap,
            "  截至时间: %s" % args.until if args.until else ""))
    else:
        print("未知策略: %s" % strategy_id)
        sys.exit(1)

    # 扫描
    results = scan(codes, date, strategy_id, args.n, until_hour=until_hour, until_minute=until_minute,
                   change_min=args.change_min, change_max=args.change_max, **strategy_kwargs)

    # 输出
    print_results(results, strategy_id, date)

    # 导出
    if args.csv:
        export_results(results, strategy_id, date)

    # 导出代码
    if args.output:
        export_codes(results, strategy_id, date)

    # 额外打印命中股票代码
    if args.print_codes and results:
        print("\n========== 命中股票 ==========\n\n\n")
        for r in results:
            print("%s" % r['code'])
        print("\n\n")


if __name__ == '__main__':
    main()
