"""
上证指数爬虫调用示例

功能：
- 展示ShIndexSpider的基本使用
- 获取日线、周线、月线数据
- 不同指数代码示例

运行方式：
    python spider/sh_index/example_sh_index.py

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import sys
import os
import pandas as pd

# 添加项目路径
project_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_path)

from spider.sh_index import ShIndexSpider

# 设置pandas显示格式
pd.options.display.float_format = '{:.2f}'.format
pd.options.display.max_columns = 10
pd.options.display.width = 120


def demo_daily():
    """示例1：获取日线数据"""
    print("=" * 60)
    print("示例1：获取上证指数日线数据")
    print("=" * 60)

    spider = ShIndexSpider()

    # 获取上证指数日线
    df = spider.get_daily('zs_000001', '20260101', '20260624')

    if df.empty:
        print("数据获取失败（可能是网络问题）")
        return

    print(f"\n数据行数: {len(df)}")
    print(f"数据字段: {list(df.columns)}")

    # 显示前5行
    print("\n前5行数据：")
    print(df.head())

    # 显示后5行
    print("\n后5行数据：")
    print(df.tail())

    # 基本统计
    print("\n基本统计：")
    print(f"  日期范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
    print(f"  最高点: {df['high'].max()}")
    print(f"  最低点: {df['low'].min()}")
    print(f"  平均成交量: {df['volume'].mean():.0f}")


def demo_weekly():
    """示例2：获取周线数据"""
    print("\n" + "=" * 60)
    print("示例2：获取上证指数周线数据")
    print("=" * 60)

    spider = ShIndexSpider()
    df = spider.get_weekly('zs_000001', '20260101', '20260624')

    if df.empty:
        print("数据获取失败")
        return

    print(f"\n周线数据: {len(df)}行")
    print(df[['date', 'open', 'close', 'high', 'low', 'volume']].head(10))


def demo_monthly():
    """示例3：获取月线数据"""
    print("\n" + "=" * 60)
    print("示例3：获取上证指数月线数据")
    print("=" * 60)

    spider = ShIndexSpider()
    df = spider.get_monthly('zs_000001', '20250101', '20260624')

    if df.empty:
        print("数据获取失败")
        return

    print(f"\n月线数据: {len(df)}行")
    print(df[['date', 'open', 'close', 'high', 'low', 'volume']])


def demo_multi_index():
    """示例4：获取不同指数数据"""
    print("\n" + "=" * 60)
    print("示例4：获取不同指数数据")
    print("=" * 60)

    spider = ShIndexSpider()

    indices = [
        ('zs_000001', '上证指数'),
        ('zs_399001', '深证成指'),
        ('zs_399006', '创业板指'),
    ]

    for code, name in indices:
        df = spider.get_daily(code, '20260601', '20260624')

        if df.empty:
            print(f"\n{name}({code}): 获取失败")
            continue

        print(f"\n{name}({code}):")
        print(f"  数据行数: {len(df)}")
        print(f"  最新收盘: {df['close'].iloc[-1]}")
        print(f"  区间最高: {df['high'].max()}")
        print(f"  区间最低: {df['low'].min()}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("上证指数爬虫调用示例")
    print("=" * 60)

    try:
        demo_daily()
        # demo_weekly()
        # demo_monthly()
        # demo_multi_index()

        print("\n" + "=" * 60)
        print("✅ 所有示例完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()