"""
快速测试脚本 - 用于验证数据层功能

直接运行此脚本可以快速测试所有功能
"""

import sys
import os
import pandas as pd

# 添加项目路径到sys.path（examples目录的父目录）
project_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_path)

# 设置pandas显示格式：保留两位小数
pd.options.display.float_format = '{:.2f}'.format

# 使用绝对导入
from pystock_data.basic import BasicBars, BasicMinutes, BasicMinutesWithVR
from pystock_data.indicators import KDJIndicator, MACDIndicator, MAIndicator

def test_basic_bars():
    """测试基础K线数据"""
    print("=" * 60)
    print("测试1: 基础K线数据获取")
    print("=" * 60)
    
    bars = BasicBars()
    
    # 测试日线
    print("\n测试日线数据（000400）:")
    day_df = bars.get_daily('000400', 10)
    print(f"✅ 获取成功，数据行数: {len(day_df)}")
    print(f"字段列表: {list(day_df.columns)}")
    print("\n前3行数据:")
    print(day_df.head(3))
    
    # 测试周线
    print("\n测试周线数据:")
    week_df = bars.get_weekly('000400', 10)
    print(f"✅ 获取成功，数据行数: {len(week_df)}")
    
    # 测试月线
    print("\n测试月线数据:")
    month_df = bars.get_monthly('000400', 10)
    print(f"✅ 获取成功，数据行数: {len(month_df)}")

def test_basic_minutes():
    """测试基础分时数据"""
    print("\n" + "=" * 60)
    print("测试2: 基础分时数据获取")
    print("=" * 60)
    
    minutes = BasicMinutes()
    
    # 测试分时数据
    print("\n测试分时数据（000400, 20260624）:")
    minute_df = minutes.get_data('000400', '20260624')
    print(f"✅ 获取成功，数据行数: {len(minute_df)}")
    print(f"字段列表: {list(minute_df.columns)}")
    print("\n前5行数据:")
    print(minute_df.head(5))

def test_kdj_indicator():
    """测试KDJ指标"""
    print("\n" + "=" * 60)
    print("测试3: KDJ指标计算")
    print("=" * 60)
    
    bars = BasicBars()
    kdj = KDJIndicator()
    
    # 获取基础数据
    basic_df = bars.get_daily('000400', 30)
    
    # 计算KDJ指标
    print("\n计算KDJ指标:")
    kdj_df = kdj.calculate(basic_df)
    print(f"✅ 计算成功")
    print(f"新增字段: kdj_k, kdj_d, kdj_j")
    print("\n包含KDJ的数据:")
    print(kdj_df[['stock_code', 'trade_date', 'close', 'kdj_k', 'kdj_d', 'kdj_j']].head(5))

def test_macd_indicator():
    """测试MACD指标"""
    print("\n" + "=" * 60)
    print("测试4: MACD指标计算")
    print("=" * 60)
    
    bars = BasicBars()
    macd = MACDIndicator()
    
    # 获取基础数据
    basic_df = bars.get_daily('000400', 35)
    
    # 计算MACD指标
    print("\n计算MACD指标:")
    macd_df = macd.calculate(basic_df)
    print(f"✅ 计算成功")
    print(f"新增字段: macd_dif, macd_dea, macd_macd")
    print("\n包含MACD的数据:")
    print(macd_df[['stock_code', 'trade_date', 'close', 'macd_dif', 'macd_dea', 'macd_macd']].tail(5))

def test_basic_minutes_with_vr():
    """测试带量比的分时数据"""
    print("\n" + "=" * 60)
    print("测试5: 带量比的分时数据（BasicMinutesWithVR）")
    print("=" * 60)

    minutes_vr = BasicMinutesWithVR()

    # 获取带量比的分时数据（自动获取过去5日日线数据）
    print("\n获取带量比的分时数据（000400, 20260624, n=5）:")
    vr_df = minutes_vr.get_data('000400', '20260624', n=5)
    print(f"✅ 获取成功，数据行数: {len(vr_df)}")
    
    # 显示过去5日分钟均量
    avg_vol = minutes_vr.get_avg_vol_per_minute()
    print(f"\n过去5日分钟均量: {avg_vol:.2f}")
    
    # 显示昨收价
    prev_close = minutes_vr.get_prev_close()
    print(f"昨收价: {prev_close:.2f}")

    # 显示新增字段
    print(f"新增字段: volume_ratio, cumulative_vol, time_index, avg_vol_per_minute")
    print("\n包含量比的数据（前10分钟）:")
    print(vr_df[['stock_code', 'datetime', 'volume', 'cumulative_vol', 'volume_ratio', 'time_index']].head(10))

    # 分析量比数据
    print("\n量比数据分析:")
    summary = minutes_vr.get_volume_ratio_summary(vr_df)
    print(f"最大量比: {summary['max']:.2f}")
    print(f"最小量比: {summary['min']:.2f}")
    print(f"平均量比: {summary['avg']:.2f}")
    print(f"当前量比: {summary['current']:.2f}")

    # 量比趋势分析
    trend = minutes_vr.get_volume_ratio_trend(vr_df, window=10)
    print(f"\n量比趋势（窗口=10）: {trend}")

    # 量比活跃度分析
    high_vr = minutes_vr.filter_volume_ratio_by_range(vr_df, min_vr=2.0)
    print(f"\n量比>=2.0的分钟数: {len(high_vr)}")
    print(f"占比: {len(high_vr) / len(vr_df) * 100:.1f}%")

    # 量比峰值时段
    peaks = minutes_vr.find_volume_ratio_peaks(vr_df, threshold=3.0)
    if peaks:
        print(f"\n量比峰值时段（>=3.0）:")
        for time_str, vr_value in peaks[:5]:  # 显示前5个峰值
            print(f"  {time_str}: {vr_value:.2f}")

def test_combined_indicators():
    """测试组合多个指标"""
    print("\n" + "=" * 60)
    print("测试6: 组合多个指标")
    print("=" * 60)
    
    bars = BasicBars()
    kdj = KDJIndicator()
    macd = MACDIndicator()
    ma = MAIndicator()
    
    # 获取基础数据
    basic_df = bars.get_daily('000400', 100)
    print(f"\n基础数据: {len(basic_df)}行")
    
    # 逐步添加指标
    enhanced_df = basic_df.copy()
    
    # 添加KDJ
    enhanced_df = kdj.calculate(enhanced_df)
    print(f"✅ 添加KDJ指标")
    
    # 添加MACD
    enhanced_df = macd.calculate(enhanced_df)
    print(f"✅ 添加MACD指标")
    
    # 添加均线
    enhanced_df = ma.calculate(enhanced_df)
    print(f"✅ 添加均线指标")
    
    # 显示最终数据
    print(f"\n最终数据字段数: {len(enhanced_df.columns)}")
    print(f"所有字段: {list(enhanced_df.columns)}")
    print("\n最终数据前3行:")
    print(enhanced_df.head(3))

def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("PyStock数据层功能测试")
    print("=" * 60)
    
    try:
        test_basic_bars()
        test_basic_minutes()
        test_kdj_indicator()
        test_macd_indicator()
        test_basic_minutes_with_vr()
        test_combined_indicators()

        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()