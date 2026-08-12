"""
MA指标动态参数示例

功能：
- 展示MA指标支持运行时动态传入周期参数
- 演示三种使用方式：默认周期、初始化自定义、运行时动态

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import sys
import os
import pandas as pd

# 添加项目路径到sys.path
project_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_path)

# 设置pandas显示格式：保留两位小数
pd.options.display.float_format = '{:.2f}'.format

# 使用绝对导入
from pystock_data.basic import BasicBars
from pystock_data.indicators import MAIndicator


def demo_default_periods():
    """
    演示1：使用默认周期参数
    
    默认周期：[5, 10, 20, 60]
    """
    print("=" * 60)
    print("演示1：使用默认周期参数")
    print("=" * 60)
    
    # 创建MA指标实例（使用默认周期）
    ma = MAIndicator()
    
    # 获取基础数据
    bars = BasicBars()
    basic_df = bars.get_daily('000400', 100)
    
    # 使用默认周期计算均线
    result_df = ma.calculate(basic_df)
    
    print(f"\n默认周期: {ma.get_periods()}")
    print(f"计算后的字段数: {len(result_df.columns)}")
    print(f"新增均线字段: ma5, ma10, ma20, ma60")
    
    # 显示均线数据
    print("\n均线数据示例（前5行）:")
    print(result_df[['stock_code', 'trade_date', 'close', 'ma5', 'ma10', 'ma20', 'ma60']].head(5))


def demo_custom_periods_init():
    """
    演示2：初始化时设置自定义周期
    
    自定义周期：[3, 5, 7]（短线周期组合）
    """
    print("\n" + "=" * 60)
    print("演示2：初始化时设置自定义周期")
    print("=" * 60)
    
    # 创建MA指标实例（自定义周期）
    custom_periods = [3, 5, 7]  # 短线周期组合
    ma = MAIndicator(periods=custom_periods)
    
    # 获取基础数据
    bars = BasicBars()
    basic_df = bars.get_daily('000400', 100)
    
    # 使用自定义周期计算均线
    result_df = ma.calculate(basic_df)
    
    print(f"\n自定义周期: {ma.get_periods()}")
    print(f"计算后的字段数: {len(result_df.columns)}")
    print(f"新增均线字段: ma3, ma5, ma7")
    
    # 显示均线数据
    print("\n短线均线数据示例（前5行）:")
    print(result_df[['stock_code', 'trade_date', 'close', 'ma3', 'ma5', 'ma7']].head(5))


def demo_dynamic_periods_runtime():
    """
    演示3：运行时动态传入周期参数
    
    灵活使用：一个实例多次调用不同参数
    """
    print("\n" + "=" * 60)
    print("演示3：运行时动态传入周期参数")
    print("=" * 60)
    
    # 创建MA指标实例（默认周期）
    ma = MAIndicator()
    
    # 获取基础数据
    bars = BasicBars()
    basic_df = bars.get_daily('000400', 100)
    
    # 第一次：使用默认周期计算
    print("\n第一次计算 - 使用默认周期:")
    default_df = ma.calculate(basic_df)
    print(f"周期: {ma.get_periods()}")
    print(f"字段: ma5, ma10, ma20, ma60")
    print(default_df[['close', 'ma5', 'ma10']].head(3))
    
    # 第二次：运行时传入动态周期（中线组合）
    print("\n第二次计算 - 运行时传入动态周期:")
    dynamic_periods = [10, 20, 30]  # 中线周期组合
    dynamic_df = ma.calculate(basic_df, periods=dynamic_periods)
    print(f"临时周期: {dynamic_periods}")
    print(f"字段: ma10, ma20, ma30")
    print(dynamic_df[['close', 'ma10', 'ma20', 'ma30']].head(3))
    
    # 第三次：再次使用默认周期（验证不影响原设置）
    print("\n第三次计算 - 再次使用默认周期:")
    again_df = ma.calculate(basic_df)
    print(f"周期: {ma.get_periods()}（仍为默认值）")
    print(f"字段: ma5, ma10, ma20, ma60")
    print(again_df[['close', 'ma5', 'ma10']].head(3))


def demo_different_strategies():
    """
    演示4：不同策略使用不同周期组合
    
    灵活切换：短线、中线、长线策略
    """
    print("\n" + "=" * 60)
    print("演示4：不同策略使用不同周期组合")
    print("=" * 60)
    
    # 创建一个MA实例
    ma = MAIndicator()
    
    # 获取基础数据
    bars = BasicBars()
    basic_df = bars.get_daily('000400', 100)
    
    # 短线策略：快周期（3, 5, 7）
    print("\n短线策略 - 快周期均线:")
    short_df = ma.calculate(basic_df, periods=[3, 5, 7])
    print(f"周期: [3, 5, 7]")
    print(short_df[['close', 'ma3', 'ma5', 'ma7']].tail(5))
    
    # 中线策略：中周期（10, 20, 30）
    print("\n中线策略 - 中周期均线:")
    medium_df = ma.calculate(basic_df, periods=[10, 20, 30])
    print(f"周期: [10, 20, 30]")
    print(medium_df[['close', 'ma10', 'ma20', 'ma30']].tail(5))
    
    # 长线策略：慢周期（60, 120, 250）
    print("\n长线策略 - 慢周期均线:")
    long_df = ma.calculate(basic_df, periods=[60, 120, 250])
    print(f"周期: [60, 120, 250]")
    print(long_df[['close', 'ma60', 'ma120', 'ma250']].tail(5))


def demo_error_cases():
    """
    演示5：参数验证错误案例
    
    展示参数验证功能
    """
    print("\n" + "=" * 60)
    print("演示5：参数验证错误案例")
    print("=" * 60)
    
    # 创建MA指标实例
    ma = MAIndicator()
    
    # 获取基础数据
    bars = BasicBars()
    basic_df = bars.get_daily('000400', 100)
    
    # 测试错误参数
    error_cases = [
        ([], "空列表"),
        ("5,10,20", "字符串类型"),
        ([5, -10, 20], "负数周期"),
        ([5, 10.5, 20], "非整数周期"),
    ]
    
    for periods, desc in error_cases:
        print(f"\n测试错误参数 - {desc}: {periods}")
        try:
            ma.calculate(basic_df, periods=periods)
            print("❌ 未捕获错误")
        except ValueError as e:
            print(f"✅ 成功捕获错误: {e}")


def main():
    """运行所有演示"""
    print("\n" + "=" * 60)
    print("MA指标动态参数功能演示")
    print("=" * 60)
    
    try:
        demo_default_periods()
        demo_custom_periods_init()
        demo_dynamic_periods_runtime()
        demo_different_strategies()
        demo_error_cases()
        
        print("\n" + "=" * 60)
        print("✅ 所有演示完成！")
        print("=" * 60)
        print("\n关键特性总结：")
        print("1. 默认周期：[5, 10, 20, 60]")
        print("2. 初始化自定义：MAIndicator(periods=[...])")
        print("3. 运行时动态：ma.calculate(df, periods=[...])")
        print("4. 参数验证：自动检查参数合法性")
        print("5. 一个实例多次使用不同参数")
        
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()