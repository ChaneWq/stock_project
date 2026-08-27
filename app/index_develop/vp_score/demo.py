"""
量价打分指标（VP Score）演示与验证脚本

功能：
- 使用 000592 真实日线数据验证 VPScoreIndicator
- 打印逐日评分表（day_score / pattern_score / state / event）
- 形态趋势核对：只验证"启动日前分数高"等模糊特征，不核对精确分数
- 输出下游信号：蓄势预警（PULLBACK 且分数>=watch_score）、启动确认（CONFIRMED）

运行方式（项目根目录）：
    python app/index_develop/vp_score/demo.py

作者：PyStock项目组
日期：2026-08-27
版本：1.0.0
"""

import os
import sys

# 支持任意工作目录直接运行：加入项目根目录与脚本目录
_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
for _p in (_ROOT, os.path.dirname(os.path.abspath(__file__))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pandas as pd

from pystock_data.basic.bars import BasicBars
from vp_score import VPScoreIndicator

CODE = '000592'
N_DAYS = 120

# 验收基准日（000592 已收盘的稳定形态案例，仅锁定日期不锁定分数）
SIGNAL_DATE = '2026-08-18'    # 爆量信号日
CONFIRM_DATE = '2026-08-25'   # 启动确认日
# 验收标准为模糊形态核对（参数可调，分数值会变，形态特征不变）：
#   1. 正确识别信号日与启动确认日
#   2. 启动日前分数高：回调尾声分数 >= 信号日初始分
#   3. 回调期间分数整体上行，启动前夕达到峰值
#   4. 蓄势预警（分数>=watch_score）先于启动日触发


def main():
    print(f"=== 量价打分指标演示：{CODE} ===\n")

    # 1. 获取真实日线数据（最新在前，指标内部自动兼容排序）
    print("获取日线数据 ...")
    df = BasicBars().get_daily(CODE, N_DAYS)
    if df.empty:
        print("获取数据失败（网络异常），演示退出")
        sys.exit(1)
    print(f"获取成功：{len(df)} 根日K\n")

    # 2. 计算量价打分
    indicator = VPScoreIndicator()
    result = indicator.calculate(df)

    # 3. 打印评分表（时间升序，最近25个交易日）
    pd.set_option('display.width', 200)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.unicode.east_asian_width', True)
    show_cols = ['trade_date', 'close', 'pct', 'vr5', 'day_score',
                 'state', 'shrink_ratio', 'pattern_score', 'event']
    show = result.sort_values('datetime').tail(25).copy()
    show['event'] = show['event'].replace('', '-')
    print("---- 逐日评分表（最近25个交易日）----")
    print(show[show_cols].to_string(index=False))

    # 4. 模糊形态核对（核心验收：启动日前分数高，即形态成立）
    indexed = result.set_index('trade_date').sort_index()
    print("\n---- 形态趋势核对 ----")
    checks = []

    # ① 信号日识别
    if SIGNAL_DATE in indexed.index:
        checks.append(('信号日识别(08-18为SIGNAL)',
                       indexed.loc[SIGNAL_DATE, 'state'] == 'SIGNAL'))
    else:
        checks.append(('信号日识别(08-18为SIGNAL)', False))

    # ② 启动确认识别
    if CONFIRM_DATE in indexed.index:
        checks.append(('启动确认识别(08-25为CONFIRMED)',
                       indexed.loc[CONFIRM_DATE, 'state'] == 'CONFIRMED'))
    else:
        checks.append(('启动确认识别(08-25为CONFIRMED)', False))

    pullback = indexed[(indexed.index > SIGNAL_DATE) & (indexed.index < CONFIRM_DATE)]
    if not pullback.empty:
        # ③ 启动日前分数高：回调尾声分数 >= 信号日初始分
        last_score = int(pullback['pattern_score'].iloc[-1])
        signal_score = int(indexed.loc[SIGNAL_DATE, 'pattern_score'])
        checks.append((f'启动日前分数高(回调尾声{last_score}>=信号日{signal_score})',
                       last_score >= signal_score))
        # ④ 回调期间分数上行至峰值（启动前夕为期间最高分）
        max_score = int(pullback['pattern_score'].max())
        checks.append((f'回调期间分数上行至峰值(峰值{max_score}出现在启动前夕)',
                       last_score == max_score))
        # ⑤ 蓄势预警先于启动日触发
        watch_before = pullback[pullback['pattern_score'] >= indicator.watch_score]
        checks.append((f'蓄势预警先于启动日触发(分数>={indicator.watch_score})',
                       not watch_before.empty))
    else:
        checks.append(('回调期数据存在', False))

    all_pass = True
    for name, ok in checks:
        all_pass = all_pass and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"核对结果：{'全部通过' if all_pass else '形态不成立，请检查'}")

    # 5. 下游信号输出
    ascending = result.sort_values('datetime')
    watch = ascending[(ascending['state'] == 'PULLBACK')
                      & (ascending['pattern_score'] >= indicator.watch_score)]
    confirmed = ascending[ascending['state'] == 'CONFIRMED']
    print(f"\n---- 下游信号（近{N_DAYS}日）----")
    if not watch.empty:
        for _, r in watch.iterrows():
            print(f"蓄势预警: {r['trade_date']} pattern_score={int(r['pattern_score'])} "
                  f"(回调中，分数>={indicator.watch_score})")
    else:
        print("蓄势预警: 无")
    if not confirmed.empty:
        first_date = confirmed['trade_date'].iloc[0]
        print(f"启动确认: {first_date} 首次确认（后续{len(confirmed) - 1}个确认后交易日）")
    else:
        print("启动确认: 无")

    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
