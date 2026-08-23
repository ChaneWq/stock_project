"""
VWAPIndicator（分时均价线）测试demo

功能：
- 使用真实分时数据验证均价线计算正确性
- 覆盖场景：真实数据一致性、amount缺失时的估算路径、防篡改

作者：PyStock项目组
日期：2026-08-24
版本：1.0.0
"""

import os
import sys

import pandas as pd

# 支持直接运行：python vwap_demo.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from pystock_data.basic import BasicMinutes
from pystock_data.indicators import VWAPIndicator


def test_real_data():
    """测试1：真实分时数据，抽样手工核算均价"""
    code, date = '000400', '20260821'
    minute_df = BasicMinutes().get_data(code, date)
    if minute_df.empty:
        print(f"[FAIL] {code} {date} 分时数据获取失败（网络？）")
        return False

    has_amount = 'amount' in minute_df.columns
    print(f"[INFO] {code} {date} 获取{len(minute_df)}条分时数据，"
          f"amount字段: {'有(用真实成交额)' if has_amount else '无(用close*volume估算)'}")

    vwap = VWAPIndicator()
    df = vwap.calculate(minute_df)

    assert 'avg_price' in df.columns, "缺少avg_price字段"

    # 手工核算：第60分钟（11:00前）和最后一分钟的均价
    for idx in [59, len(df) - 1]:
        sub = df.iloc[:idx + 1]
        if has_amount:
            expect = sub['amount'].sum() / sub['volume'].sum()
        else:
            expect = (sub['close'] * sub['volume']).sum() / sub['volume'].sum()
        got = df['avg_price'].iloc[idx]
        assert abs(got - expect) < 0.001, f"第{idx+1}条: 期望{expect:.3f} 实际{got:.3f}"
        print(f"[OK] 第{idx+1}条分钟({df['hour'].iloc[idx]:02d}:{df['minute'].iloc[idx]:02d}) "
              f"均价={got} 手工核算={expect:.3f}")

    print("[PASS] 测试1: 真实数据均价核算一致\n")
    return True


def test_price_field():
    """测试3：price字段路径（策略层将close改名price的场景）"""
    raw = pd.DataFrame({
        'price': [10.0, 10.5, 11.0],
        'volume': [100, 200, 300],
    })
    vwap = VWAPIndicator()
    df = vwap.calculate(raw)
    assert 'avg_price' not in raw.columns, "原DataFrame被修改"
    assert list(df['avg_price']) == [10.0, 10.333, 10.667], \
        f"均价错误: {list(df['avg_price'])}"
    print("[PASS] 测试3: price字段路径正确，原数据不被修改\n")
    return True


def test_no_modify():
    """测试4：close字段路径（原始分时数据场景）"""
    raw = pd.DataFrame({
        'close': [10.0, 10.5, 11.0],
        'volume': [100, 200, 300],
    })
    vwap = VWAPIndicator()
    df = vwap.calculate(raw)
    assert 'avg_price' not in raw.columns, "原DataFrame被修改"
    assert list(df['avg_price']) == [10.0, 10.333, 10.667], \
        f"均价错误: {list(df['avg_price'])}"
    print("[PASS] 测试4: close字段路径正确，原数据不被修改\n")
    return True


def main():
    print("=" * 60)
    print("VWAPIndicator（分时均价线）测试")
    print("=" * 60 + "\n")

    ok = test_real_data()
    ok = test_price_field() and ok
    ok = test_no_modify() and ok

    print("=" * 60)
    print("全部测试通过" if ok else "存在失败项")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
