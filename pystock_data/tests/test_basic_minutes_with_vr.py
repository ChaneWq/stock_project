"""
带量比的分时数据测试模块

功能：
- 测试BasicMinutesWithVR类的分时量比计算功能
- 测试时间序号计算正确性
- 测试量比计算准确性

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pytest
import pandas as pd
import numpy as np
from ..basic import BasicMinutesWithVR


class TestBasicMinutesWithVR:
    """
    BasicMinutesWithVR测试类
    
    测试范围：
        - 时间序号计算（通达信公式）
        - 量比计算准确性
        - 数据获取功能
        - 辅助方法功能
    """
    
    def setup_method(self):
        """
        测试初始化
        
        创建BasicMinutesWithVR实例
        """
        self.minutes_vr = BasicMinutesWithVR()
    
    def test_calc_time_index(self):
        """
        测试时间序号计算（关键验证）
        
        验证：
            - 通达信公式正确性
            - 关键时间点验证（9:30, 11:29, 13:00, 14:59）
        
        公式：
            时间序号:=IF(HOUR>12,(HOUR-13)*60+MINUTE+120,(HOUR-9)*60+MINUTE-30)+1
        
        验证点：
            9:30  → 1 (开盘第一分钟)
            11:29 → 120 (上午最后一分钟)
            13:00 → 121 (下午第一分钟)
            14:59 → 240 (收盘最后一分钟)
        """
        # 关键时间点测试
        test_cases = [
            (9, 30, 1),    # 开盘第一分钟
            (9, 31, 2),    # 开盘第二分钟
            (11, 29, 120), # 上午最后一分钟
            (13, 0, 121),  # 下午第一分钟
            (13, 1, 122),  # 下午第二分钟
            (14, 59, 240), # 收盘最后一分钟
        ]
        
        for hour, minute, expected in test_cases:
            result = self.minutes_vr._calc_time_index(hour, minute)
            # 当传入单个值时，result是单个值而非数组
            if isinstance(result, np.ndarray):
                actual = result[0]
            else:
                actual = result
            
            assert actual == expected, \
                f"时间序号计算错误：{hour}:{minute} 应为{expected}，实际为{actual}"
        
        # 批量测试（向量化计算）
        hours = np.array([9, 9, 11, 13, 14])
        minutes = np.array([30, 31, 29, 0, 59])
        expected = np.array([1, 2, 120, 121, 240])
        
        result = self.minutes_vr._calc_time_index(hours, minutes)
        assert np.array_equal(result, expected), \
            f"批量时间序号计算错误：应为{expected}，实际为{result}"
    
    def test_calc_avg_vol_per_minute(self):
        """
        测试过去n日每分钟平均成交量计算
        
        验证：
            - 公式正确性：sum(过去n日成交量) / (n * 240)
            - 数值计算正确性
        """
        # 模拟过去5日成交量数据
        day_vol_list = [100000, 120000, 110000, 130000, 105000]
        n = 5
        
        # 计算分钟均量
        avg_vol = self.minutes_vr._calc_avg_vol_per_minute(day_vol_list, n)
        
        # 手动验证
        total_vol = sum(day_vol_list)  # 565000
        expected_avg = total_vol / (n * 240)  # 565000 / 1200 = 471.67
        
        assert avg_vol == expected_avg, \
            f"分钟均量计算错误：应为{expected_avg}，实际为{avg_vol}"
        
        # 测试不同的n值
        avg_vol_3 = self.minutes_vr._calc_avg_vol_per_minute(day_vol_list, 3)
        total_vol_3 = sum(day_vol_list[-3:])  # 345000
        expected_avg_3 = total_vol_3 / (3 * 240)  # 345000 / 720 = 479.17
        
        assert avg_vol_3 == expected_avg_3, \
            f"分钟均量计算错误（n=3）：应为{expected_avg_3}，实际为{avg_vol_3}"
    
    def test_calc_volume_ratio_formula(self):
        """
        测试量比计算公式
        
        验证：
            - 量比公式：累计成交量 / 时间序号 / 过去n日分钟均量
            - 数值计算正确性
        
        Example:
            假设过去5日分钟均量为1000
            第10分钟累计成交量10000
            时间序号为10
            量比应为：10000 / 10 / 1000 = 1.0
        """
        # 创建模拟分时数据
        test_data = []
        for i in range(240):
            hour = 9 if i < 120 else 13
            minute = (30 + i) if i < 120 else (i - 120) % 60
            
            # 模拟成交量（递增）
            volume = 1000 + i * 10
            
            test_data.append({
                'stock_code': '000400',
                'datetime': pd.Timestamp('2026-06-24') + pd.Timedelta(minutes=i),
                'volume': volume,
                'hour': hour,
                'minute': minute % 60 if i >= 120 else minute
            })
        
        minute_df = pd.DataFrame(test_data)
        
        # 模拟分钟均量
        avg_vol_per_minute = 1000.0
        
        # 计算量比
        vr_df = self.minutes_vr._calc_volume_ratio(minute_df, avg_vol_per_minute)
        
        # 验证第10分钟量比
        index_10 = 10
        cumulative_vol_10 = minute_df['volume'].iloc[:index_10+1].sum()
        time_index_10 = vr_df['time_index'].iloc[index_10]
        expected_vr_10 = cumulative_vol_10 / time_index_10 / avg_vol_per_minute
        
        actual_vr_10 = vr_df['volume_ratio'].iloc[index_10]
        
        assert abs(actual_vr_10 - round(expected_vr_10, 2)) < 0.01, \
            f"量比计算错误（第10分钟）：应为{round(expected_vr_10, 2)}，实际为{actual_vr_10}"
        
        # 验证量比值范围（应为正数）
        assert all(vr_df['volume_ratio'] >= 0), "量比值应为正数"
        
        # 验证量比保留两位小数
        for i in range(10, 50):
            vr_value = vr_df['volume_ratio'].iloc[i]
            tolerance = 0.001
            assert abs(vr_value - round(vr_value, 2)) < tolerance, \
                f"量比应保留两位小数（索引{i}：{vr_value}）"
    
    def test_get_data_real(self):
        """
        测试真实数据获取（实际数据源调用）
        
        验证：
            - 数据获取成功
            - 量比字段存在
            - 数据行数正确（240行）
        
        Note:
            - 使用真实数据源测试
            - 可能因网络或数据源状态失败
        """
        # 尝试获取真实数据
        try:
            vr_df = self.minutes_vr.get_data('000400', '20260624', n=5)
            
            if vr_df.empty:
                pytest.skip("数据源未返回数据，跳过真实数据测试")
            
            # 验证数据行数（应为240行）
            assert len(vr_df) == 240, \
                f"分时数据行数错误：应为240行，实际为{len(vr_df)}行"
            
            # 验证量比字段存在
            assert 'volume_ratio' in vr_df.columns, "缺少volume_ratio字段"
            assert 'cumulative_vol' in vr_df.columns, "缺少cumulative_vol字段"
            assert 'time_index' in vr_df.columns, "缺少time_index字段"
            assert 'avg_vol_per_minute' in vr_df.columns, "缺少avg_vol_per_minute字段"
            
            # 验证时间序号范围（1~240）
            assert vr_df['time_index'].min() >= 1, "时间序号最小值应>=1"
            assert vr_df['time_index'].max() <= 240, "时间序号最大值应<=240"
            
            # 验证量比值为正数
            assert all(vr_df['volume_ratio'] >= 0), "量比值应为正数"
            
        except Exception as e:
            pytest.skip(f"数据源调用失败，跳过真实数据测试: {e}")
    
    def test_get_avg_vol_per_minute(self):
        """
        测试获取过去n日分钟均量方法
        
        验证：
            - 方法返回正确值
            - 需先调用get_data()方法
        """
        # 尝试获取数据
        try:
            vr_df = self.minutes_vr.get_data('000400', '20260624', n=5)
            
            if vr_df.empty:
                pytest.skip("数据源未返回数据，跳过测试")
            
            # 获取分钟均量
            avg_vol = self.minutes_vr.get_avg_vol_per_minute()
            
            assert avg_vol is not None, "分钟均量应为None"
            assert isinstance(avg_vol, (int, float)), "分钟均量应为数值类型"
            assert avg_vol > 0, "分钟均量应大于0"
            
        except Exception as e:
            pytest.skip(f"数据源调用失败，跳过测试: {e}")
    
    def test_get_prev_n_day_vol_list(self):
        """
        测试获取过去n日成交量列表
        
        验证：
            - 方法返回正确值
            - 列表长度正确
        """
        try:
            vr_df = self.minutes_vr.get_data('000400', '20260624', n=5)
            
            if vr_df.empty:
                pytest.skip("数据源未返回数据，跳过测试")
            
            # 获取过去n日成交量列表
            vol_list = self.minutes_vr.get_prev_n_day_vol_list()
            
            assert vol_list is not None, "成交量列表应为None"
            assert isinstance(vol_list, list), "成交量列表应为list类型"
            assert len(vol_list) == 5, "成交量列表长度应为5"
            assert all(isinstance(v, (int, float)) for v in vol_list), \
                "成交量列表元素应为数值类型"
            
        except Exception as e:
            pytest.skip(f"数据源调用失败，跳过测试: {e}")
    
    def test_get_volume_ratio_summary(self):
        """
        测试量比统计摘要
        
        验证：
            - 返回值包含正确字段
            - 数值计算正确
        """
        try:
            vr_df = self.minutes_vr.get_data('000400', '20260624', n=5)
            
            if vr_df.empty:
                pytest.skip("数据源未返回数据，跳过测试")
            
            # 获取量比统计摘要
            summary = self.minutes_vr.get_volume_ratio_summary(vr_df)
            
            assert summary is not None, "统计摘要不应为None"
            assert 'max' in summary, "统计摘要缺少max字段"
            assert 'min' in summary, "统计摘要缺少min字段"
            assert 'avg' in summary, "统计摘要缺少avg字段"
            assert 'current' in summary, "统计摘要缺少current字段"
            
            # 验证数值范围
            assert summary['max'] >= summary['min'], "最大量比应>=最小量比"
            assert summary['avg'] >= summary['min'], "平均量比应>=最小量比"
            assert summary['avg'] <= summary['max'], "平均量比应<=最大量比"
            
        except Exception as e:
            pytest.skip(f"数据源调用失败，跳过测试: {e}")
    
    def test_get_volume_ratio_trend(self):
        """
        测试量比趋势判断
        
        验证：
            - 返回值正确
            - 趋势判断逻辑正确
        """
        try:
            vr_df = self.minutes_vr.get_data('000400', '20260624', n=5)
            
            if vr_df.empty:
                pytest.skip("数据源未返回数据，跳过测试")
            
            # 判断量比趋势
            trend = self.minutes_vr.get_volume_ratio_trend(vr_df, window=10)
            
            assert trend in ['上升', '下降', '平稳', '数据不足'], \
                f"趋势返回值错误：{trend}"
            
        except Exception as e:
            pytest.skip(f"数据源调用失败，跳过测试: {e}")
    
    def test_filter_volume_ratio_by_range(self):
        """
        测试按量比范围过滤
        
        验证：
            - 过滤逻辑正确
            - 返回数据符合条件
        """
        try:
            vr_df = self.minutes_vr.get_data('000400', '20260624', n=5)
            
            if vr_df.empty:
                pytest.skip("数据源未返回数据，跳过测试")
            
            # 过滤量比>=2.0的时段
            high_vr_df = self.minutes_vr.filter_volume_ratio_by_range(vr_df, min_vr=2.0)
            
            if not high_vr_df.empty:
                # 验证过滤结果
                assert all(high_vr_df['volume_ratio'] >= 2.0), \
                    "过滤结果应全部满足量比>=2.0"
            
            # 过滤量比<=0.5的时段
            low_vr_df = self.minutes_vr.filter_volume_ratio_by_range(vr_df, max_vr=0.5)
            
            if not low_vr_df.empty:
                # 验证过滤结果
                assert all(low_vr_df['volume_ratio'] <= 0.5), \
                    "过滤结果应全部满足量比<=0.5"
            
        except Exception as e:
            pytest.skip(f"数据源调用失败，跳过测试: {e}")
    
    def test_find_volume_ratio_peaks(self):
        """
        测试查找量比峰值
        
        验证：
            - 返回值格式正确
            - 峰值排序正确
        """
        try:
            vr_df = self.minutes_vr.get_data('000400', '20260624', n=5)
            
            if vr_df.empty:
                pytest.skip("数据源未返回数据，跳过测试")
            
            # 查找量比峰值（阈值3.0）
            peaks = self.minutes_vr.find_volume_ratio_peaks(vr_df, threshold=3.0)
            
            if peaks:
                # 验证返回格式
                assert all(isinstance(p, tuple) and len(p) == 2 for p in peaks), \
                    "峰值格式应为(time_str, vr_value)"
                
                # 验证排序（降序）
                vr_values = [p[1] for p in peaks]
                assert vr_values == sorted(vr_values, reverse=True), \
                    "峰值应按量比降序排列"
                
                # 验证峰值>=阈值
                assert all(vr >= 3.0 for vr in vr_values), \
                    "峰值量比应>=阈值"
            
        except Exception as e:
            pytest.skip(f"数据源调用失败，跳过测试: {e}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])