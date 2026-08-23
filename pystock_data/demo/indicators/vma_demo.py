"""
成交量均线指标（VMA）测试Demo

功能：
- 使用真实日线数据验证 VolumeMAIndicator 的计算结果
- 数据来源：BasicBars.get_daily（通达信数据源）

作者：PyStock项目组
日期：2026-08-24
版本：1.0.0

运行方式：
    cd g:\pystock3\newproject
    python -m pystock_data.demo.indicators.vma_demo
"""

import pandas as pd
import sys
import os

# 支持直接运行：将项目根目录加入sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from pystock_data.basic import BasicBars
from pystock_data.indicators import VolumeMAIndicator

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
        - get_daily 返回最新在第一行（倒序），rolling计算需转为正序
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
    用原始成交量手工核对vma计算结果（真实数据一致性校验）

    Args:
        df (DataFrame): 原始日线数据（时间正序）
        result (DataFrame): 指标计算结果
    """
    # 核对最后一行：最近5日成交量均值
    manual_vma5 = round(df['volume'].tail(5).mean(), 2)
    actual_vma5 = result['vma5'].iloc[-1]
    assert abs(actual_vma5 - manual_vma5) < 0.01, \
        f"vma5核对失败: 指标值{actual_vma5} vs 手工值{manual_vma5}"
    print(f"[核对] 最近5日成交量均值 = {manual_vma5}，vma5指标值 = {actual_vma5} 一致")

    # 核对最后一行vma10：最近10日成交量均值
    manual_vma10 = round(df['volume'].tail(10).mean(), 2)
    actual_vma10 = result['vma10'].iloc[-1]
    assert abs(actual_vma10 - manual_vma10) < 0.01, \
        f"vma10核对失败: 指标值{actual_vma10} vs 手工值{manual_vma10}"
    print(f"[核对] 最近10日成交量均值 = {manual_vma10}，vma10指标值 = {actual_vma10} 一致")


def main():
    print(f"获取 {STOCK_CODE} 最近{BAR_COUNT}个交易日日线数据...")

    try:
        df = fetch_real_data(STOCK_CODE, BAR_COUNT)
    except RuntimeError as e:
        print(f"错误: {e}")
        sys.exit(1)

    print(f"获取成功，共{len(df)}条记录（{df['trade_date'].iloc[0]} ~ {df['trade_date'].iloc[-1]}）\n")

    # 计算成交量均线（vma5 + vma10）
    vma = VolumeMAIndicator(periods=[5, 10])
    result = vma.calculate(df)

    # 真实数据一致性核对
    verify_with_raw_data(df, result)

    # 展示最近10个交易日结果
    print(f"\n最近10个交易日成交量均线（{STOCK_CODE}）:")
    print(result[['trade_date', 'volume', 'vma5', 'vma10']].tail(10).to_string(index=False))

    # 简单放量/缩量参考：最新成交量与vma5的比值
    latest_volume = result['volume'].iloc[-1]
    latest_vma5 = result['vma5'].iloc[-1]
    ratio = latest_volume / latest_vma5
    state = "放量" if ratio > 1.5 else ("缩量" if ratio < 0.7 else "持平")
    print(f"\n[参考] 最新成交量 {latest_volume}，vma5 {latest_vma5}，量比 {ratio:.2f}（{state}）")


if __name__ == '__main__':
    main()
