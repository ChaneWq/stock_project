"""
量涨跌幅指标（VCHG）测试Demo

功能：
- 使用真实日线数据验证 VolumeChangeRateIndicator 的计算结果
- 数据来源：BasicBars.get_daily（通达信数据源）
- 覆盖场景：真实数据一致性、首行NaN、昨日量为0的NaN处理

作者：PyStock项目组
日期：2026-09-27
版本：1.0.0

运行方式：
    cd g:\pystock3\newproject
    python -m pystock_data.demo.indicators.vchg_demo
"""

import math
import sys
import os

import pandas as pd

# 支持直接运行：将项目根目录加入sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from pystock_data.basic import BasicBars
from pystock_data.indicators import VolumeChangeRateIndicator

# 默认股票代码与获取的交易日数量
STOCK_CODE = '000400'
BAR_COUNT = 30


def fetch_real_data(code: str, n: int) -> pd.DataFrame:
    """
    获取真实日线数据并转为时间正序

    Args:
        code (str): 股票代码（6位字符串）
        n (int): 获取的交易日数量

    Returns:
        DataFrame: 时间正序的日线数据（最新在最后一行）

    Note:
        - get_daily 返回最新在第一行（倒序），环比计算需转为正序
        - 网络失败或数据为空时抛出RuntimeError
    """
    bars = BasicBars()
    df = bars.get_daily(code, n)

    if df.empty:
        raise RuntimeError(f"获取 {code} 日线数据失败（网络异常或数据为空）")

    # 倒序转正序：shift(1)取昨日量需按时间先后排列
    return df.sort_values('datetime', ascending=True).reset_index(drop=True)


def verify_with_raw_data(df: pd.DataFrame, result: pd.DataFrame):
    """
    用原始成交量手工核对vchg计算结果（真实数据一致性校验）

    Args:
        df (DataFrame): 原始日线数据（时间正序）
        result (DataFrame): 指标计算结果
    """
    # 核对最后一行：(今日量 − 昨日量) ÷ 昨日量 × 100
    today_vol = df['volume'].iloc[-1]
    prev_vol = df['volume'].iloc[-2]
    manual_vchg = round((today_vol - prev_vol) / prev_vol * 100, 2)
    actual_vchg = result['vchg'].iloc[-1]
    assert abs(actual_vchg - manual_vchg) < 0.01, \
        f"vchg核对失败: 指标值{actual_vchg} vs 手工值{manual_vchg}"
    print(f"[核对] 最后一行: 今日量{today_vol} 昨日量{prev_vol}，"
          f"手工值{manual_vchg}% 指标值{actual_vchg}% 一致")

    # 核对首行：无昨日数据应为NaN
    assert math.isnan(result['vchg'].iloc[0]), "首行vchg应为NaN"
    print("[核对] 首行无昨日数据，vchg = NaN 一致")


def test_edge_cases():
    """测试2：构造数据覆盖昨日量为0的场景（应为NaN）"""
    raw = pd.DataFrame({
        'volume': [0.0, 1000.0, 1500.0],
    })
    vchg = VolumeChangeRateIndicator()
    df = vchg.calculate(raw)
    assert 'vchg' not in raw.columns, "原DataFrame被修改"
    assert math.isnan(df['vchg'].iloc[0]), "首行应为NaN"
    assert math.isnan(df['vchg'].iloc[1]), "昨日量为0时应为NaN"
    assert abs(df['vchg'].iloc[2] - 50.0) < 0.001, f"第三行应为50.0，实际{df['vchg'].iloc[2]}"
    print("[PASS] 测试2: 昨日量为0输出NaN，正常数据计算正确，原数据不被修改\n")
    return True


def main():
    print("=" * 60)
    print("VolumeChangeRateIndicator（量涨跌幅）测试")
    print("=" * 60 + "\n")

    # 测试1：真实数据一致性
    print(f"获取 {STOCK_CODE} 最近{BAR_COUNT}个交易日日线数据...")
    try:
        df = fetch_real_data(STOCK_CODE, BAR_COUNT)
    except RuntimeError as e:
        print(f"错误: {e}")
        sys.exit(1)

    print(f"获取成功，共{len(df)}条记录（{df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}）\n")

    # 计算量涨跌幅
    vchg = VolumeChangeRateIndicator()
    result = vchg.calculate(df)

    # 真实数据一致性核对
    verify_with_raw_data(df, result)
    print("[PASS] 测试1: 真实数据一致性核对\n")

    # 测试2：边界场景
    ok = test_edge_cases()

    # 展示最近10个交易日结果
    print(f"最近10个交易日量涨跌幅（{STOCK_CODE}）:")
    print(result[['trade_date', 'volume', 'vchg']].tail(10).to_string(index=False))

    # 简单放量/缩量参考：最新量涨跌幅
    latest_vchg = result['vchg'].iloc[-1]
    if math.isnan(latest_vchg):
        state = "无数据"
    elif latest_vchg > 50:
        state = "显著放量"
    elif latest_vchg > 0:
        state = "温和放量"
    elif latest_vchg < -30:
        state = "显著缩量"
    else:
        state = "温和缩量"
    print(f"\n[参考] 最新量涨跌幅 {latest_vchg}%（{state}）")

    print("\n" + "=" * 60)
    print("全部测试通过" if ok else "存在失败项")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
