"""
爬虫子项目测试模块

功能：
- 测试ShIndexSpider上证指数爬虫
- 测试CalendarSpider日历爬虫

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pytest
import pandas as pd
from ..sh_index import ShIndexSpider
from ..calendar import CalendarSpider


class TestShIndexSpider:
    """
    ShIndexSpider测试类
    """
    
    def setup_method(self):
        """测试初始化"""
        self.spider = ShIndexSpider()
    
    def test_get_daily(self):
        """测试获取日线数据"""
        df = self.spider.get_daily('zs_000001', '20260101', '20260624')
        
        if df.empty:
            pytest.skip("数据源未返回数据")
        
        # 验证数据不为空
        assert len(df) > 0
        
        # 验证字段存在
        expected_cols = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_pct']
        for col in expected_cols:
            assert col in df.columns, f"缺少字段: {col}"
        
        # 验证日期排序
        assert df['date'].is_monotonic_increasing, "日期应升序排列"
        
        print(f"\n日线数据: {len(df)}行")
        print(df.head())
    
    def test_get_weekly(self):
        """测试获取周线数据"""
        df = self.spider.get_weekly('zs_000001', '20260101', '20260624')
        
        if df.empty:
            pytest.skip("数据源未返回数据")
        
        assert len(df) > 0
        assert 'date' in df.columns
        
        print(f"\n周线数据: {len(df)}行")
    
    def test_get_monthly(self):
        """测试获取月线数据"""
        df = self.spider.get_monthly('zs_000001', '20260101', '20260624')
        
        if df.empty:
            pytest.skip("数据源未返回数据")
        
        assert len(df) > 0
        assert 'date' in df.columns
        
        print(f"\n月线数据: {len(df)}行")
    
    def test_parse_response(self):
        """测试JSONP解析"""
        # 模拟JSONP响应
        mock_response = 'historySearchHandler([{"code":"zs_000001","status":0,"hq":[["2026-06-24","3200","3210","10","0.31%","3190","3215","100000","500000","1.2"]]}]);'
        
        data = self.spider._parse_response(mock_response)
        
        assert data['code'] == 'zs_000001'
        assert len(data['hq']) == 1
    
    def test_to_dataframe(self):
        """测试DataFrame转换"""
        mock_data = {
            'code': 'zs_000001',
            'status': 0,
            'hq': [
                ['2026-06-24', '3200', '3210', '10', '0.31%', '3190', '3215', '100000', '500000', '1.2'],
                ['2026-06-23', '3180', '3200', '20', '0.63%', '3170', '3210', '120000', '600000', '1.5']
            ]
        }
        
        df = self.spider._to_dataframe(mock_data)
        
        assert len(df) == 2
        assert 'date' in df.columns
        assert 'open' in df.columns
        assert 'close' in df.columns
        
        # 验证日期升序
        assert df['date'].iloc[0] == '2026-06-23'
        assert df['date'].iloc[1] == '2026-06-24'


class TestCalendarSpider:
    """
    CalendarSpider测试类
    """
    
    def setup_method(self):
        """测试初始化"""
        self.spider = CalendarSpider()
    
    def test_generate_date_range(self):
        """测试日期范围生成"""
        date_list = self.spider._generate_date_range('2026-06-01', '2026-06-05')
        
        assert len(date_list) == 5
        assert date_list[0] == '2026-06-01'
        assert date_list[-1] == '2026-06-05'
    
    def test_build_url(self):
        """测试URL构建"""
        url = self.spider._build_url('2026-06-24')
        
        assert '2026-06-24' in url
        assert 'wannianrili' in url
    
    def test_parse_lunar_date(self):
        """测试农历日期解析"""
        # 测试正常农历日期
        month, day = self.spider._parse_lunar_date('五月初十')
        assert month == '五月'
        assert day == '初十'
        
        # 测试空字符串
        month, day = self.spider._parse_lunar_date('')
        assert month == ''
        assert day == ''
    
    def test_get_calendar(self):
        """测试获取日历数据"""
        # 测试小范围数据
        df = self.spider.get_calendar('2026-06-01', '2026-06-05', delay=0.1)
        
        if df.empty:
            pytest.skip("数据源未返回数据")
        
        assert len(df) > 0
        assert 'date' in df.columns
        
        print(f"\n日历数据: {len(df)}行")
        print(df[['date', 'weekday', 'lunar_date']].head())
    
    def test_get_trade_calendar(self):
        """测试获取交易日历"""
        df = self.spider.get_trade_calendar('2026-06-01', '2026-06-05', delay=0.1)
        
        if df.empty:
            pytest.skip("数据源未返回数据")
        
        # 验证不包含周末
        if len(df) > 0:
            has_weekend = df['weekday'].str.contains('六|日').any()
            assert not has_weekend, "交易日历不应包含周末"
        
        print(f"\n交易日历: {len(df)}行")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])