"""
BasicMinutes（基础分时数据）测试demo

功能：
- 使用真实分时数据验证 BasicMinutes 的数据获取与标准化字段
- 覆盖场景：字段完整性、240分钟完整性、时间排序、hour/minute字段、
  空数据处理、日期范围查询占位（NotImplementedError）

作者：PyStock项目组
日期：2026-10-24
版本：1.0.0
"""

import os
import sys

import pandas as pd

# 支持直接运行：python minutes_demo.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from pystock_data.basic import BasicMinutes

# 实际返回的标准字段（TDX历史分时源只有price/volume，open/high/low/close同值，无amount）
EXPECTED_COLUMNS = [
    'stock_code', 'datetime', 'trade_date', 'open', 'close', 'high', 'low',
    'volume', 'hour', 'minute'
]


def test_basic_fetch():
    """测试1：获取真实分时数据，校验字段与结构"""
    code, date = '000400', '20261023'  # 分时数据源只保留近期交易日
    minutes = BasicMinutes()
    df = minutes.get_data(code, date)

    if df.empty:
        print(f"[FAIL] {code} {date} 分时数据获取失败（非交易日或网络问题）")
        return False

    # 字段完整性
    missing = [c for c in EXPECTED_COLUMNS if c not in df.columns]
    assert not missing, f"缺少字段: {missing}"
    print(f"[OK] {code} {date} 获取{len(df)}条分时数据，字段完整（{len(df.columns)}列）")

    # stock_code / trade_date 标准化
    assert (df['stock_code'] == code).all(), "stock_code与请求代码不一致"
    assert df['trade_date'].nunique() == 1, "trade_date应只有一天"
    expect_date = f"{date[:4]}-{date[4:6]}-{date[6:]}"
    assert df['trade_date'].iloc[0] == expect_date, \
        f"trade_date应为YYYY-MM-DD格式，实际: {df['trade_date'].iloc[0]}"
    print(f"[OK] stock_code={df['stock_code'].iloc[0]}, "
          f"trade_date={df['trade_date'].iloc[0]}（YYYY-MM-DD格式）")

    # 时间排序（正序）
    assert df['datetime'].is_monotonic_increasing, "数据应按时间正序排列"
    print(f"[OK] 时间正序排列: 首条={df['datetime'].iloc[0]}, 末条={df['datetime'].iloc[-1]}")

    # hour/minute字段
    first = df.iloc[0]
    last = df.iloc[-1]
    assert (first['hour'], first['minute']) == (9, 30), \
        f"首条应为9:30，实际{first['hour']}:{first['minute']}"
    assert (last['hour'], last['minute']) == (14, 59), \
        f"末条应为14:59，实际{last['hour']}:{last['minute']}"
    print(f"[OK] hour/minute字段: 首条{first['hour']:02d}:{first['minute']:02d} -> "
          f"末条{last['hour']:02d}:{last['minute']:02d}")

    # 240分钟完整性（A股全天分钟数）
    assert len(df) == 240, f"应为240条分钟数据，实际{len(df)}条"
    print("[OK] 分时数据240分钟完整")

    # 打印样例（前3条 + 后3条）
    cols = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    print("\n----- 前3条 -----")
    print(df[cols].head(3).to_string(index=False))
    print("----- 后3条 -----")
    print(df[cols].tail(3).to_string(index=False))

    print("[PASS] 测试1: 真实分时数据字段与结构正确\n")
    return True


def test_empty_data():
    """测试2：无效日期返回空DataFrame且不抛异常"""
    df = BasicMinutes().get_data('000400', '20260101')  # 元旦假期
    assert isinstance(df, pd.DataFrame), "应返回DataFrame"
    assert df.empty, "非交易日应返回空DataFrame"
    print("[PASS] 测试2: 非交易日返回空DataFrame，不抛异常\n")
    return True


def test_range_not_implemented():
    """测试3：日期范围查询为待实现占位"""
    try:
        BasicMinutes().get_data_by_range('000400', '20260620', '20260624')
        print("[FAIL] 应抛出NotImplementedError")
        return False
    except NotImplementedError:
        print("[PASS] 测试3: get_data_by_range按预期抛出NotImplementedError\n")
        return True


def main():
    print("=" * 60)
    print("BasicMinutes 分时数据 demo")
    print("=" * 60 + "\n")

    results = [
        test_basic_fetch,
        test_empty_data,
        test_range_not_implemented,
    ]
    passed = sum(bool(fn()) for fn in results)

    print("=" * 60)
    print(f"结果: {passed}/{len(results)} 通过")
    print("=" * 60)
    return passed == len(results)


if __name__ == '__main__':
    sys.exit(0 if main() else 1)
