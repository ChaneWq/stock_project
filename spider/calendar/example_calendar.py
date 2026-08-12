"""
日历数据爬虫调用示例

功能：
- 展示CalendarSpider的基本使用
- 获取日历数据（阳历、农历、干支）
- 获取交易日历

运行方式：
    python spider/calendar/example_calendar.py

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

from spider.calendar import CalendarSpider

# 设置pandas显示格式
pd.options.display.max_columns = 15
pd.options.display.width = 200


def demo_calendar():
    """示例1：获取日历数据"""
    print("=" * 60)
    print("示例1：获取日历数据")
    print("=" * 60)

    spider = CalendarSpider()

    # 获取2026年6月日历数据
    df = spider.get_calendar('2026-06-01', '2026-06-30', delay=0.3)

    if df.empty:
        print("数据获取失败（可能是网络问题）")
        return

    print(f"\n数据行数: {len(df)}")
    print(f"数据字段: {list(df.columns)}")

    # 显示前10行
    print("\n前10行数据：")
    display_cols = ['date', 'weekday', 'lunar_date', 'ganzhi_year', 'zodiac_year', 'festival']
    available_cols = [c for c in display_cols if c in df.columns]
    print(df[available_cols].head(10))


def demo_trade_calendar():
    """示例2：获取交易日历"""
    print("\n" + "=" * 60)
    print("示例2：获取交易日历（过滤周末）")
    print("=" * 60)

    spider = CalendarSpider()

    # 获取2026年6月交易日历
    df = spider.get_trade_calendar('2026-06-01', '2026-06-30', delay=0.3)

    if df.empty:
        print("数据获取失败")
        return

    print(f"\n交易日数: {len(df)}天")

    # 显示交易日
    display_cols = ['date', 'weekday', 'lunar_date']
    available_cols = [c for c in display_cols if c in df.columns]
    print(df[available_cols])


def demo_short_range():
    """示例3：获取小范围日历数据"""
    print("\n" + "=" * 60)
    print("示例3：获取小范围日历数据（单周）")
    print("=" * 60)

    spider = CalendarSpider()

    # 获取一周日历数据
    df = spider.get_calendar('2026-06-23', '2026-06-27', delay=0.3)

    if df.empty:
        print("数据获取失败")
        return

    print(f"\n日历数据: {len(df)}天")

    # 显示完整字段
    print("\n完整日历信息：")
    for _, row in df.iterrows():
        print(f"\n  日期: {row['date']} {row.get('weekday', '')}")
        print(f"  农历: {row.get('lunar_date', '')}")
        print(f"  干支: {row.get('ganzhi_year', '')}年 {row.get('ganzhi_month', '')}月 {row.get('ganzhi_day', '')}日")
        print(f"  生肖: {row.get('zodiac_year', '')}")
        if row.get('festival'):
            print(f"  节日: {row['festival']}")


def main():
    """运行所有示例"""
    print("\n" + "=" * 60)
    print("日历数据爬虫调用示例")
    print("=" * 60)

    try:
        demo_calendar()
        # demo_trade_calendar()
        # demo_short_range()

        print("\n" + "=" * 60)
        print("✅ 所有示例完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 示例执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()