"""
MA7线上连续爬升选股器演示与验证脚本

功能：
- 使用 002134 真实日线数据验证 Ma7StreakSelector（strict/near 双模式）
- 打印双模式逐日 streak 对照表
- 模糊形态核对（不核对精确分数，只验证形态特征）：
  起点/断裂/贴线容错/终止/入选/新周期重算
- 输出两模式的全部入选日与最新交易日汇总

运行方式（项目根目录）：
    python app/stock_selection/ma7_streak/demo.py

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
from ma7_streak import Ma7StreakSelector

CODE = '002134'
N_DAYS = 120

# 验收基准日（002134 已收盘的稳定形态案例）
START_DATE = '2026-08-04'    # streak 起点（放量突破站上MA7）
STRICT_LAST = '2026-08-13'   # strict 基准日（streak=8，入选）
STRICT_BREAK = '2026-08-14'  # strict 断裂日（-0.01%贴线跌破）
NEAR_KEEP = '2026-08-14'     # near 贴线容错日（streak延续=9）
NEAR_LAST = '2026-08-18'     # near 基准日（streak=11，入选）
NEAR_BREAK = '2026-08-19'    # near 明显破位终止日（-5.31%）
RESTART_DATE = '2026-08-27'  # 涨停日，新streak重新起算


def main():
    print(f"=== MA7线上连续爬升选股器演示：{CODE} ===\n")

    # 1. 获取真实日线数据
    print("获取日线数据 ...")
    df = BasicBars().get_daily(CODE, N_DAYS)
    if df.empty:
        print("获取数据失败（网络异常），演示退出")
        sys.exit(1)
    print(f"获取成功：{len(df)} 根日K\n")

    # 2. 双模式逐日计算
    strict = Ma7StreakSelector(mode='strict')
    near = Ma7StreakSelector(mode='near', near_tolerance=0.01)
    s_strict = strict.analyze_series(df)
    s_near = near.analyze_series(df)

    # 3. 双模式逐日对照表（时间升序，最近20个交易日）
    pd.set_option('display.width', 200)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.unicode.east_asian_width', True)
    a = s_strict.sort_values('datetime').tail(20)[['trade_date', 'close', 'pct', 'ma7', 'dev_pct']]
    b = s_strict.sort_values('datetime').tail(20)[['streak']].reset_index(drop=True)
    c = s_near.sort_values('datetime').tail(20)[['streak']].reset_index(drop=True)
    table = pd.concat([a.reset_index(drop=True), b, c], axis=1)
    table.columns = ['trade_date', 'close', 'pct', 'ma7', 'dev_pct',
                     'streak_strict', 'streak_near']
    print("---- 双模式逐日streak对照（最近20个交易日）----")
    print(table.to_string(index=False))

    # 4. 模糊形态核对（核心验收：形态特征成立）
    idx_s = s_strict.set_index('trade_date')
    idx_n = s_near.set_index('trade_date')
    print("\n---- 形态核对 ----")
    checks = [
        ('起点识别(08-04 strict streak=1)',
         idx_s.loc[START_DATE, 'streak'] == 1),
        ('起点前一日(08-03 strict streak=0)',
         idx_s.loc['2026-08-03', 'streak'] == 0),
        ('strict: 08-13 streak=8',
         idx_s.loc[STRICT_LAST, 'streak'] == 8),
        ('strict: 08-14 贴线跌破即断裂(streak=0)',
         idx_s.loc[STRICT_BREAK, 'streak'] == 0),
        ('strict: 08-13 满足入选条件',
         bool(idx_s.loc[STRICT_LAST, 'is_candidate'])),
        ('near: 08-14 贴线容错不断裂(streak=9)',
         idx_n.loc[NEAR_KEEP, 'streak'] == 9),
        ('near: 08-18 streak=11',
         idx_n.loc[NEAR_LAST, 'streak'] == 11),
        ('near: 08-19 明显破位终止(streak=0)',
         idx_n.loc[NEAR_BREAK, 'streak'] == 0),
        ('near: 08-18 满足入选条件',
         bool(idx_n.loc[NEAR_LAST, 'is_candidate'])),
        ('新周期重算(08-27 双模式 streak=1)',
         idx_s.loc[RESTART_DATE, 'streak'] == 1 and idx_n.loc[RESTART_DATE, 'streak'] == 1),
    ]
    all_pass = True
    for name, ok in checks:
        all_pass = all_pass and ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
    print(f"核对结果：{'全部通过' if all_pass else '形态不成立，请检查'}")

    # 5. 全部入选日回放（近N_DAYS日）
    cand_s = s_strict[s_strict['is_candidate']].sort_values('datetime')
    cand_n = s_near[s_near['is_candidate']].sort_values('datetime')
    print(f"\n---- 入选日回放（近{N_DAYS}日）----")
    print(f"strict模式入选日: {list(cand_s['trade_date']) if not cand_s.empty else '无'}")
    print(f"near模式入选日:   {list(cand_n['trade_date']) if not cand_n.empty else '无'}")

    # 6. 最新交易日汇总（双模式 analyze 接口演示）
    print("\n---- 最新交易日汇总（analyze接口）----")
    for label, sel in (('strict', strict), ('near', near)):
        r = sel.analyze(df)
        print(f"[{label}] {r['trade_date']} close={r['close']} ma7={r['ma7']} "
              f"streak_days={r['streak_days']} streak_start={r['streak_start']} "
              f"small_ratio={r['small_candle_ratio']} slope={r['ma7_slope_pct']}% "
              f"dev={r['dev_pct']}% is_candidate={r['is_candidate']}")

    return 0 if all_pass else 1


if __name__ == '__main__':
    sys.exit(main())
