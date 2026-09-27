"""
MA斜率指标（MASlope）测试Demo

功能：
- 使用真实日线数据验证 MASlopeIndicator 的计算结果
- 数据来源：BasicBars.get_daily（通达信数据源）
- 覆盖场景：真实数据一致性、前k行NaN、基准MA为0、ks运行时覆盖

作者：PyStock项目组
日期：2026-09-27
版本：1.0.0

运行方式：
    cd g:\pystock3\newproject
    python -m pystock_data.demo.indicators.maslope_demo
"""

import math
import sys
import os

import pandas as pd

# 支持直接运行：将项目根目录加入sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from pystock_data.basic import BasicBars
from pystock_data.indicators import MASlopeIndicator

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

    # 倒序转正序：shift(k)取k日前MA需按时间先后排列
    return df.sort_values('datetime', ascending=True).reset_index(drop=True)


def verify_with_raw_data(df: pd.DataFrame, result: pd.DataFrame):
    """
    用原始收盘价手工核对ma7_slope1计算结果（真实数据一致性校验）

    Args:
        df (DataFrame): 原始日线数据（时间正序）
        result (DataFrame): 指标计算结果
    """
    # 核对最后一行：最近7日均值 vs 前一个7日窗口均值
    ma7_today = df['close'].tail(7).mean()
    ma7_prev = df['close'].iloc[-8:-1].mean()
    manual_slope = round((ma7_today - ma7_prev) / ma7_prev * 100, 2)
    actual_slope = result['ma7_slope1'].iloc[-1]
    assert abs(actual_slope - manual_slope) < 0.01, \
        f"ma7_slope1核对失败: 指标值{actual_slope} vs 手工值{manual_slope}"
    print(f"[核对] 最后一行: MA7={ma7_today:.3f} 昨日MA7={ma7_prev:.3f}，"
          f"手工值{manual_slope}% 指标值{actual_slope}% 一致")

    # 核对首行：无昨日MA应为NaN
    assert math.isnan(result['ma7_slope1'].iloc[0]), "首行ma7_slope1应为NaN"
    print("[核对] 首行无昨日MA，ma7_slope1 = NaN 一致")


def test_edge_cases():
    """测试2：构造数据覆盖边界场景（前k行NaN、基准MA为0、ks运行时覆盖）"""
    # 场景A：等差数列close，前7行部分窗口MA，验证斜率数值与前k行NaN
    raw = pd.DataFrame({'close': [float(i) for i in range(1, 10)]})  # 1~9
    maslope = MASlopeIndicator(n=7, ks=[1])
    df = maslope.calculate(raw)
    assert 'ma7_slope1' not in raw.columns, "原DataFrame被修改"
    # MA(部分窗口): 1, 1.5, 2, 2.5, 3, 3.5, 4, 5, 6
    assert math.isnan(df['ma7_slope1'].iloc[0]), "首行应为NaN"
    assert abs(df['ma7_slope1'].iloc[1] - 50.0) < 0.001, \
        f"第二行应为50.0，实际{df['ma7_slope1'].iloc[1]}"
    print("[PASS] 测试2A: 等差数列斜率计算正确，首行NaN，原数据不被修改")

    # 场景B：基准MA为0（前7个收盘价全为0），除零应输出NaN
    raw_zero = pd.DataFrame({'close': [0.0] * 7 + [5.0]})
    df_zero = maslope.calculate(raw_zero)
    # 第7行MA7=0，第8行MA7=5/7，斜率=inf → NaN
    assert math.isnan(df_zero['ma7_slope1'].iloc[7]), "基准MA为0时应为NaN"
    print("[PASS] 测试2B: 基准MA为0输出NaN")

    # 场景C：ks运行时覆盖，一次计算多个偏移
    df_multi = maslope.calculate(raw, ks=[1, 2])
    assert 'ma7_slope1' in df_multi.columns and 'ma7_slope2' in df_multi.columns, \
        "ks=[1,2]应输出ma7_slope1和ma7_slope2"
    assert math.isnan(df_multi['ma7_slope2'].iloc[1]), "slope2第二行应为NaN（仅1日前基准）"
    print("[PASS] 测试2C: ks运行时覆盖输出多斜率字段，前k行NaN正确")

    return True


def main():
    print("=" * 60)
    print("MASlopeIndicator（MA斜率）测试")
    print("=" * 60 + "\n")

    # 测试1：真实数据一致性
    print(f"获取 {STOCK_CODE} 最近{BAR_COUNT}个交易日日线数据...")
    try:
        df = fetch_real_data(STOCK_CODE, BAR_COUNT)
    except RuntimeError as e:
        print(f"错误: {e}")
        sys.exit(1)

    print(f"获取成功，共{len(df)}条记录（{df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}）\n")

    # 计算MA斜率（默认n=7, ks=[1]）
    maslope = MASlopeIndicator()
    result = maslope.calculate(df)

    # 真实数据一致性核对
    verify_with_raw_data(df, result)
    print("[PASS] 测试1: 真实数据一致性核对\n")

    # 测试2：边界场景
    ok = test_edge_cases()

    # 展示最近10个交易日结果
    print(f"最近10个交易日MA7斜率（{STOCK_CODE}）:")
    print(result[['trade_date', 'close', 'ma7_slope1']].tail(10).to_string(index=False))

    # 简单趋势方向参考：最新MA7斜率
    latest_slope = result['ma7_slope1'].iloc[-1]
    if math.isnan(latest_slope):
        state = "无数据"
    elif latest_slope > 0.5:
        state = "均线上行（加速）"
    elif latest_slope > 0:
        state = "均线上行（放缓）"
    elif latest_slope < -0.5:
        state = "均线下行（加速）"
    else:
        state = "均线下行（放缓）"
    print(f"\n[参考] 最新MA7斜率 {latest_slope}%（{state}）")

    print("\n" + "=" * 60)
    print("全部测试通过" if ok else "存在失败项")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
