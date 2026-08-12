"""
分时量比完整演示示例

功能：
- 展示BasicMinutesWithVR的基本使用
- 演示量比分析功能（统计、趋势、过滤、峰值）
- 对比BasicMinutes和BasicMinutesWithVR的区别
- 多股票批量分析示例
- 量比应用场景演示

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import sys
import os

# 添加项目路径到sys.path
project_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_path)

from pystock_data.basic import BasicMinutes, BasicMinutesWithVR
import pandas as pd

# 设置pandas显示格式：保留两位小数
pd.options.display.float_format = '{:.2f}'.format


def demo_basic_usage():
    """
    演示1：基本使用
    
    展示BasicMinutesWithVR的基本功能和数据获取
    """
    print("=" * 60)
    print("演示1：BasicMinutesWithVR基本使用")
    print("=" * 60)
    
    # 创建BasicMinutesWithVR实例
    minutes_vr = BasicMinutesWithVR()
    
    # 获取带量比的分时数据（自动获取过去5日日线数据）
    print("\n获取带量比的分时数据：")
    print("-" * 60)
    
    vr_df = minutes_vr.get_data('000400', '20260630', n=5)
    
    if vr_df.empty:
        print("数据获取失败，跳过演示")
        return
    
    print(f"✅ 数据获取成功")
    print(f"  数据行数: {len(vr_df)}")
    print(f"  数据字段: {list(vr_df.columns)}")
    
    # 显示过去5日分钟均量
    avg_vol = minutes_vr.get_avg_vol_per_minute()
    print(f"\n过去5日分钟均量: {avg_vol:.2f}")
    print(f"  （量比计算基准）")
    
    # 显示昨收价
    prev_close = minutes_vr.get_prev_close()
    print(f"昨收价: {prev_close:.2f}")
    
    # 显示量比数据（前10分钟）
    print("\n量比数据（前10分钟）：")
    print(vr_df[['datetime', 'volume', 'cumulative_vol', 'volume_ratio', 'time_index']].head(10))
    
    # 显示量比数据（最后10分钟）
    print("\n量比数据（最后10分钟）：")
    print(vr_df[['datetime', 'volume', 'cumulative_vol', 'volume_ratio', 'time_index']].tail(10))


def demo_volume_ratio_analysis():
    """
    演示2：量比分析功能
    
    展示量比统计分析、趋势判断、过滤和峰值查找
    """
    print("\n" + "=" * 60)
    print("演示2：量比分析功能")
    print("=" * 60)
    
    minutes_vr = BasicMinutesWithVR()
    vr_df = minutes_vr.get_data('000400', '20260624', n=5)
    
    if vr_df.empty:
        print("数据获取失败，跳过演示")
        return
    
    # 量比统计摘要
    print("\n量比统计摘要：")
    print("-" * 60)
    
    summary = minutes_vr.get_volume_ratio_summary(vr_df)
    print(f"最大量比: {summary['max']:.2f}")
    print(f"最小量比: {summary['min']:.2f}")
    print(f"平均量比: {summary['avg']:.2f}")
    print(f"当前量比: {summary['current']:.2f}")
    
    # 量比趋势判断
    print("\n量比趋势判断：")
    print("-" * 60)
    
    trend = minutes_vr.get_volume_ratio_trend(vr_df, window=10)
    print(f"量比趋势（窗口=10分钟）: {trend}")
    
    # 量比含义分析
    print("\n量比含义分析：")
    print("-" * 60)
    
    max_vr = summary['max']
    min_vr = summary['min']
    avg_vr = summary['avg']
    
    if max_vr > 3:
        print(f"✅ 最大量比 {max_vr} > 3：明显放量（活跃时段）")
    elif max_vr > 2:
        print(f"✅ 最大量比 {max_vr} > 2：放量（活跃时段）")
    else:
        print(f"✅ 最大量比 {max_vr}：正常（无异常放量）")
    
    if min_vr < 0.5:
        print(f"✅ 最小量比 {min_vr} < 0.5：明显缩量（清淡时段）")
    elif min_vr < 1:
        print(f"✅ 最小量比 {min_vr} < 1：缩量（清淡时段）")
    else:
        print(f"✅ 最小量比 {min_vr}：正常（无异常缩量）")
    
    if avg_vr > 1:
        print(f"✅ 平均量比 {avg_vr} > 1：整体放量")
    elif avg_vr < 1:
        print(f"✅ 平均量比 {avg_vr} < 1：整体缩量")
    else:
        print(f"✅ 平均量比 {avg_vr}：整体正常")


def demo_volume_ratio_filtering():
    """
    演示3：量比过滤功能
    
    展示按量比范围过滤时段、查找量比峰值
    """
    print("\n" + "=" * 60)
    print("演示3：量比过滤功能")
    print("=" * 60)
    
    minutes_vr = BasicMinutesWithVR()
    vr_df = minutes_vr.get_data('000400', '20260624', n=5)
    
    if vr_df.empty:
        print("数据获取失败，跳过演示")
        return
    
    # 过滤放量时段（量比 >= 2.0）
    print("\n过滤放量时段（量比 >= 2.0）：")
    print("-" * 60)
    
    high_vr = minutes_vr.filter_volume_ratio_by_range(vr_df, min_vr=2.0)
    print(f"放量分钟数: {len(high_vr)}")
    print(f"占比: {len(high_vr) / len(vr_df) * 100:.1f}%")
    
    if not high_vr.empty:
        print("\n放量时段详情（前5分钟）：")
        print(high_vr[['datetime', 'volume', 'volume_ratio']].head(5))
    
    # 过滤缩量时段（量比 <= 0.8）
    print("\n过滤缩量时段（量比 <= 0.8）：")
    print("-" * 60)
    
    low_vr = minutes_vr.filter_volume_ratio_by_range(vr_df, max_vr=0.8)
    print(f"缩量分钟数: {len(low_vr)}")
    print(f"占比: {len(low_vr) / len(vr_df) * 100:.1f}%")
    
    if not low_vr.empty:
        print("\n缩量时段详情（前5分钟）：")
        print(low_vr[['datetime', 'volume', 'volume_ratio']].head(5))
    
    # 查找量比峰值时段（量比 >= 3.0）
    print("\n查找量比峰值时段（量比 >= 3.0）：")
    print("-" * 60)
    
    peaks = minutes_vr.find_volume_ratio_peaks(vr_df, threshold=3.0)
    
    if peaks:
        print(f"量比峰值时段数: {len(peaks)}")
        print("\n峰值时段详情（按量比降序）：")
        for time_str, vr_value in peaks:
            print(f"  {time_str}: {vr_value}")
    else:
        print("未发现量比峰值时段（量比 >= 3.0）")


def demo_compare_basic_minutes():
    """
    演示4：对比BasicMinutes和BasicMinutesWithVR
    
    展示两种分时数据类的区别和使用场景
    """
    print("\n" + "=" * 60)
    print("演示4：对比BasicMinutes和BasicMinutesWithVR")
    print("=" * 60)
    
    print("\n功能对比：")
    print("-" * 60)
    
    # BasicMinutes：普通分时数据
    print("BasicMinutes（普通分时）：")
    minutes = BasicMinutes()
    minute_df = minutes.get_data('000400', '20260624')
    
    print(f"  ✅ 数据行数: {len(minute_df)}")
    print(f"  ✅ 数据字段: {[f for f in minute_df.columns if 'volume_ratio' not in f]}")
    print(f"  ✅ 特点: 快速、轻量、单日数据")
    print(f"  ✅ 适用: 查看分时走势、简单分时分析")
    
    # BasicMinutesWithVR：带量比的分时数据
    print("\nBasicMinutesWithVR（带量比分时）：")
    minutes_vr = BasicMinutesWithVR()
    vr_df = minutes_vr.get_data('000400', '20260624', n=5)
    
    print(f"  ✅ 数据行数: {len(vr_df)}")
    print(f"  ✅ 数据字段: 包含volume_ratio等量比字段")
    print(f"  ✅ 特点: 自动获取过去n日数据、计算量比")
    print(f"  ✅ 适用: 分时量比分析、异常监控、活跃度判断")
    
    # 数据依赖对比
    print("\n数据依赖对比：")
    print("-" * 60)
    
    print("BasicMinutes:")
    print("  - 数据需求: 当日240分钟分时数据")
    print("  - 数据源调用: 1次（fetch_minutes）")
    print("  - 性能: 快速（无额外历史数据）")
    
    print("\nBasicMinutesWithVR:")
    print("  - 数据需求: 当日分时 + 过去n日日线数据")
    print("  - 数据源调用: 2次（fetch_minutes + fetch_prev_n_day_vol）")
    print("  - 性能: 相对较慢（需额外历史数据）")
    
    # 使用场景对比
    print("\n使用场景对比：")
    print("-" * 60)
    
    print("✅ 使用BasicMinutes场景：")
    print("  - 快速查看当日分时走势")
    print("  - 分时价格变动分析")
    print("  - 不需要量比数据的场景")
    print("  - 实时盘中监控（仅价格）")
    
    print("\n✅ 使用BasicMinutesWithVR场景：")
    print("  - 分时量比分析")
    print("  - 成交量活跃度判断")
    print("  - 异常放量/缩量监控")
    print("  - 分时成交量对比分析")
    print("  - 策略应用中的量比过滤")


def demo_multiple_stocks_analysis():
    """
    演示5：多股票批量分析
    
    展示如何批量分析多只股票的量比情况
    """
    print("\n" + "=" * 60)
    print("演示5：多股票批量量比分析")
    print("=" * 60)
    
    stock_codes = ['000400', '000001', '600000']
    date = '20260624'
    n = 5
    
    print(f"\n分析股票列表: {stock_codes}")
    print(f"分析日期: {date}")
    print(f"历史天数: {n}日")
    print("-" * 60)
    
    # 批量获取数据并分析
    results = []
    
    for code in stock_codes:
        minutes_vr = BasicMinutesWithVR()
        vr_df = minutes_vr.get_data(code, date, n)
        
        if vr_df.empty:
            print(f"⚠️ {code}: 数据获取失败")
            continue
        
        # 获取量比统计
        summary = minutes_vr.get_volume_ratio_summary(vr_df)
        avg_vol = minutes_vr.get_avg_vol_per_minute()
        
        results.append({
            'code': code,
            'avg_vol': avg_vol,
            'max_vr': summary['max'],
            'min_vr': summary['min'],
            'avg_vr': summary['avg'],
            'current_vr': summary['current'],
            'data_rows': len(vr_df)
        })
        
        print(f"✅ {code}: 数据获取成功")
    
    # 显示批量分析结果
    if results:
        print("\n批量分析结果：")
        print("-" * 60)
        
        results_df = pd.DataFrame(results)
        print(results_df[['code', 'avg_vol', 'max_vr', 'min_vr', 'avg_vr', 'current_vr']])
        
        # 排序分析
        print("\n按平均量比排序：")
        print("-" * 60)
        
        sorted_by_avg = results_df.sort_values('avg_vr', ascending=False)
        print(sorted_by_avg[['code', 'avg_vr', 'max_vr', 'min_vr']])
        
        print("\n按最大量比排序：")
        print("-" * 60)
        
        sorted_by_max = results_df.sort_values('max_vr', ascending=False)
        print(sorted_by_max[['code', 'max_vr', 'avg_vr']])
        
        # 活跃度判断
        print("\n活跃度判断：")
        print("-" * 60)
        
        for result in results:
            avg_vr = result['avg_vr']
            code = result['code']
            
            if avg_vr > 1.5:
                activity = "活跃（整体放量）"
            elif avg_vr > 1:
                activity = "正常偏活跃"
            elif avg_vr < 0.8:
                activity = "清淡（整体缩量）"
            else:
                activity = "正常"
            
            print(f"{code}: {activity}（平均量比={avg_vr:.2f}）")


def demo_time_period_analysis():
    """
    演示6：时段分析
    
    展示不同时段的量比特征分析
    """
    print("\n" + "=" * 60)
    print("演示6：时段量比分析")
    print("=" * 60)
    
    minutes_vr = BasicMinutesWithVR()
    vr_df = minutes_vr.get_data('000400', '20260624', n=5)
    
    if vr_df.empty:
        print("数据获取失败，跳过演示")
        return
    
    # 上午时段（9:30-11:30）
    print("\n上午时段（9:30-11:30）：")
    print("-" * 60)
    
    morning_vr = vr_df[vr_df['hour'] < 12]
    morning_avg = morning_vr['volume_ratio'].mean()
    morning_max = morning_vr['volume_ratio'].max()
    
    print(f"上午分钟数: {len(morning_vr)}")
    print(f"上午平均量比: {morning_avg:.2f}")
    print(f"上午最大量比: {morning_max:.2f}")
    
    # 下午时段（13:00-15:00）
    print("\n下午时段（13:00-15:00）：")
    print("-" * 60)
    
    afternoon_vr = vr_df[vr_df['hour'] >= 13]
    afternoon_avg = afternoon_vr['volume_ratio'].mean()
    afternoon_max = afternoon_vr['volume_ratio'].max()
    
    print(f"下午分钟数: {len(afternoon_vr)}")
    print(f"下午平均量比: {afternoon_avg:.2f}")
    print(f"下午最大量比: {afternoon_max:.2f}")
    
    # 开盘半小时（9:30-10:00）
    print("\n开盘半小时（9:30-10:00）：")
    print("-" * 60)
    
    opening_vr = vr_df[
        (vr_df['hour'] == 9) &
        (vr_df['minute'] >= 30) &
        (vr_df['minute'] <= 59)
    ]
    
    if not opening_vr.empty:
        opening_avg = opening_vr['volume_ratio'].mean()
        opening_max = opening_vr['volume_ratio'].max()
        
        print(f"开盘半小时分钟数: {len(opening_vr)}")
        print(f"开盘半小时平均量比: {opening_avg:.2f}")
        print(f"开盘半小时最大量比: {opening_max:.2f}")
        
        if opening_avg > 2:
            print(f"✅ 开盘活跃：平均量比 {opening_avg:.2f} > 2")
        elif opening_avg > 1.5:
            print(f"✅ 开盘较活跃：平均量比 {opening_avg:.2f} > 1.5")
        else:
            print(f"✅ 开盘正常：平均量比 {opening_avg:.2f}")
    
    # 收盘半小时（14:30-15:00）
    print("\n收盘半小时（14:30-15:00）：")
    print("-" * 60)
    
    closing_vr = vr_df[vr_df['hour'] == 14]
    
    if not closing_vr.empty:
        closing_avg = closing_vr['volume_ratio'].mean()
        closing_max = closing_vr['volume_ratio'].max()
        
        print(f"收盘半小时分钟数: {len(closing_vr)}")
        print(f"收盘半小时平均量比: {closing_avg:.2f}")
        print(f"收盘半小时最大量比: {closing_max:.2f}")
        
        if closing_avg > 1.5:
            print(f"✅ 收盘活跃：平均量比 {closing_avg:.2f} > 1.5")
        elif closing_avg < 0.8:
            print(f"✅ 收盘清淡：平均量比 {closing_avg:.2f} < 0.8")
        else:
            print(f"✅ 收盘正常：平均量比 {closing_avg:.2f}")
    
    # 时段对比
    print("\n时段量比对比：")
    print("-" * 60)
    
    print(f"上午平均量比: {morning_avg:.2f}")
    print(f"下午平均量比: {afternoon_avg:.2f}")
    
    if morning_avg > afternoon_avg:
        print("✅ 上午时段更活跃（量比高于下午）")
    elif afternoon_avg > morning_avg:
        print("✅ 下午时段更活跃（量比高于上午）")
    else:
        print("✅ 上午下午时段活跃度相近")


def demo_volume_ratio_application():
    """
    演示7：量比应用场景
    
    展示量比在实际应用中的使用方法
    """
    print("\n" + "=" * 60)
    print("演示7：量比应用场景")
    print("=" * 60)
    
    minutes_vr = BasicMinutesWithVR()
    vr_df = minutes_vr.get_data('000400', '20260624', n=5)
    
    if vr_df.empty:
        print("数据获取失败，跳过演示")
        return
    
    # 场景1：异常放量监控
    print("\n场景1：异常放量监控（量比 >= 3.0）：")
    print("-" * 60)
    
    peaks = minutes_vr.find_volume_ratio_peaks(vr_df, threshold=3.0)
    
    if peaks:
        print(f"发现异常放量时段: {len(peaks)}个")
        for time_str, vr_value in peaks[:3]:
            print(f"  ⚠️ {time_str}: 量比{vr_value}（明显放量）")
    else:
        print("未发现异常放量时段")
    
    # 场景2：缩量预警
    print("\n场景2：缩量预警（量比 < 0.5）：")
    print("-" * 60)
    
    very_low_vr = minutes_vr.filter_volume_ratio_by_range(vr_df, max_vr=0.5)
    
    if not very_low_vr.empty:
        print(f"发现缩量时段: {len(very_low_vr)}分钟")
        print(f"  ⚠️ 缩量时段占比: {len(very_low_vr) / len(vr_df) * 100:.1f}%")
    else:
        print("未发现明显缩量时段")
    
    # 场景3：活跃时段筛选
    print("\n场景3：活跃时段筛选（量比 >= 2.0）：")
    print("-" * 60)
    
    active_vr = minutes_vr.filter_volume_ratio_by_range(vr_df, min_vr=2.0)
    
    if not active_vr.empty:
        print(f"活跃时段: {len(active_vr)}分钟")
        print(f"  ✅ 活跃时段占比: {len(active_vr) / len(vr_df) * 100:.1f}%")
        
        # 分析活跃时段的时间分布
        active_hours = active_vr.groupby('hour').size()
        print("\n活跃时段时间分布：")
        for hour, count in active_hours.items():
            print(f"  {hour}时: {count}分钟")
    else:
        print("未发现活跃时段")
    
    # 场景4：量比趋势监控
    print("\n场景4：量比趋势监控：")
    print("-" * 60)
    
    trend = minutes_vr.get_volume_ratio_trend(vr_df, window=20)
    print(f"量比趋势（窗口=20分钟）: {trend}")
    
    if trend == '上升':
        print("  ✅ 量比上升趋势：成交量逐渐放大")
    elif trend == '下降':
        print("  ✅ 量比下降趋势：成交量逐渐萎缩")
    else:
        print("  ✅ 量比平稳趋势：成交量稳定")


def main():
    """运行所有演示"""
    print("\n" + "=" * 60)
    print("分时量比完整演示")
    print("=" * 60)
    
    try:
        demo_basic_usage()
        # demo_volume_ratio_analysis()
        # demo_volume_ratio_filtering()
        # demo_compare_basic_minutes()
        # demo_multiple_stocks_analysis()
        # demo_time_period_analysis()
        # demo_volume_ratio_application()
        
        print("\n" + "=" * 60)
        print("✅ 所有演示完成！")
        print("=" * 60)
        
        print("\n关键要点总结：")
        print("1. **BasicMinutesWithVR**：自动获取过去n日数据计算量比")
        print("2. **量比公式**：累计成交量 / 时间序号 / 过去n日分钟均量")
        print("3. **量比含义**：")
        print("   - >3：明显放量（异常活跃）")
        print("   - 2~3：放量（活跃）")
        print("   - 1~2：正常")
        print("   - 0.5~1：缩量（清淡）")
        print("   - <0.5：明显缩量（异常清淡）")
        print("4. **应用场景**：")
        print("   - 异常放量监控")
        print("   - 缩量预警")
        print("   - 活跃时段筛选")
        print("   - 量比趋势监控")
        print("5. **时段分析**：开盘、盘中、收盘时段量比特征")
        print("6. **批量分析**：多股票量比对比")
        
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()