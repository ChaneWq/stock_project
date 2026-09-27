"""
MA偏离度指标（MABias）测试Demo

功能：
- 使用真实日线数据验证 MABiasIndicator 的计算结果
- 数据来源：BasicBars.get_daily（通达信数据源）
- 覆盖场景：真实数据一致性、MA为0的NaN处理、periods运行时覆盖

作者：PyStock项目组
日期：2026-09-27
版本：1.0.0

运行方式：
    cd g:\pystock3\newproject
    python -m pystock_data.demo.indicators.mabias_demo
"""

import math
import sys
import os

import pandas as pd

# 支持直接运行：将项目根目录加入sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from pystock_data.basic import BasicBars
from pystock_data.indicators import MABiasIndicator

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
        - get_daily 返回最新在第一行（倒序），乖离率计算需转为正序
        - 网络失败或数据为空时抛出RuntimeError
    """
    bars = BasicBars()
    df = bars.get_daily(code, n)

    if df.empty:
        raise RuntimeError(f"获取 {code} 日线数据失败（网络异常或数据为空）")

    # 倒序转正序：rolling窗口按时间先后计算
    return df.sort_values('datetime', ascending=True).reset_index(drop=True)


def verify_with_raw_data(df: pd.DataFrame, result: pd.DataFrame):
    """
    用原始收盘价手工核对bias7计算结果（真实数据一致性校验）

    Args:
        df (DataFrame): 原始日线数据（时间正序）
        result (DataFrame): 指标计算结果
    """
    # 核对最后一行：(收盘价 − 最近7日均值) ÷ 最近7日均值 × 100
    close = df['close'].iloc[-1]
    ma7 = df['close'].tail(7).mean()
    manual_bias = round((close - ma7) / ma7 * 100, 2)
    actual_bias = result['bias7'].iloc[-1]
    assert abs(actual_bias - manual_bias) < 0.01, \
        f"bias7核对失败: 指标值{actual_bias} vs 手工值{manual_bias}"
    print(f"[核对] 最后一行: close={close} MA7={ma7:.3f}，"
          f"手工值{manual_bias}% 指标值{actual_bias}% 一致")

    # MA部分窗口补齐，乖离率从首行起应有值（无NaN）
    assert not result['bias7'].isna().any(), "部分窗口补齐下bias7不应有NaN"
    print("[核对] MA部分窗口补齐，bias7全行有值 一致")


def test_edge_cases():
    """测试2：构造数据覆盖边界场景（MA为0、periods运行时覆盖、防篡改）"""
    mabias = MABiasIndicator()

    # 场景A：前7个收盘价全为0，第7行MA7=0，0/0应输出NaN
    raw_zero = pd.DataFrame({'close': [0.0] * 7 + [5.0]})
    df_zero = mabias.calculate(raw_zero)
    assert 'bias7' not in raw_zero.columns, "原DataFrame被修改"
    assert math.isnan(df_zero['bias7'].iloc[6]), "MA为0时应为NaN"
    # 第8行: close=5, MA7=5/7 → bias = 600.0
    assert abs(df_zero['bias7'].iloc[7] - 600.0) < 0.001, \
        f"第8行应为600.0，实际{df_zero['bias7'].iloc[7]}"
    print("[PASS] 测试2A: MA为0输出NaN，正常数据计算正确，原数据不被修改")

    # 场景B：等差数列close，验证乖离率数值与periods运行时覆盖
    raw = pd.DataFrame({'close': [float(i) for i in range(1, 10)]})  # 1~9
    df_multi = mabias.calculate(raw, periods=[7, 20])
    assert 'bias7' in df_multi.columns and 'bias20' in df_multi.columns, \
        "periods=[7,20]应输出bias7和bias20"
    # 最后一行: close=9, MA7=6 → (9-6)/6*100 = 50.0
    assert abs(df_multi['bias7'].iloc[-1] - 50.0) < 0.001, \
        f"最后一行应为50.0，实际{df_multi['bias7'].iloc[-1]}"
    print("[PASS] 测试2B: periods运行时覆盖输出多周期字段，数值正确")

    return True


def main():
    print("=" * 60)
    print("MABiasIndicator（MA偏离度）测试")
    print("=" * 60 + "\n")

    # 测试1：真实数据一致性
    print(f"获取 {STOCK_CODE} 最近{BAR_COUNT}个交易日日线数据...")
    try:
        df = fetch_real_data(STOCK_CODE, BAR_COUNT)
    except RuntimeError as e:
        print(f"错误: {e}")
        sys.exit(1)

    print(f"获取成功，共{len(df)}条记录（{df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}）\n")

    # 计算MA偏离度（默认periods=[7]）
    mabias = MABiasIndicator()
    result = mabias.calculate(df)

    # 真实数据一致性核对
    verify_with_raw_data(df, result)
    print("[PASS] 测试1: 真实数据一致性核对\n")

    # 测试2：边界场景
    ok = test_edge_cases()

    # 展示最近10个交易日结果
    print(f"最近10个交易日MA7偏离度（{STOCK_CODE}）:")
    print(result[['trade_date', 'close', 'bias7']].tail(10).to_string(index=False))

    # 简单超买超卖参考：最新乖离率
    latest_bias = result['bias7'].iloc[-1]
    if math.isnan(latest_bias):
        state = "无数据"
    elif latest_bias > 5:
        state = "严重正乖离（超买倾向）"
    elif latest_bias > 0:
        state = "正乖离（价格在MA7上方）"
    elif latest_bias < -5:
        state = "严重负乖离（超卖倾向）"
    else:
        state = "负乖离（价格在MA7下方）"
    print(f"\n[参考] 最新bias7 {latest_bias}%（{state}）")

    print("\n" + "=" * 60)
    print("全部测试通过" if ok else "存在失败项")
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
