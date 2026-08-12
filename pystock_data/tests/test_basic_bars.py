"""
基础数据测试模块

功能：
- 测试BasicBars类的日线、周线、月线获取功能
- 测试数据标准化
- 测试数据完整性

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pytest
import pandas as pd
from ..basic import BasicBars


class TestBasicBars:
    """
    BasicBars测试类
    
    测试范围：
        - 日线数据获取
        - 周线数据获取
        - 月线数据获取
        - 数据字段完整性
    """
    
    def setup_method(self):
        """
        测试初始化
        
        创建BasicBars实例
        """
        self.bars = BasicBars()
        self.test_code = '000400'  # 测试股票代码
    
    def test_get_daily(self):
        """
        测试获取日线数据
        
        验证：
            - 返回DataFrame非空
            - 字段完整性
            - 数据排序正确
        """
        df = self.bars.get_daily(self.test_code, n=400)
        
        # 验证DataFrame非空
        assert not df.empty, "日线数据不应为空"
        
        # 验证必需字段存在
        required_fields = ['stock_code', 'datetime', 'trade_date', 
                           'open', 'close', 'high', 'low', 'volume']
        for field in required_fields:
            assert field in df.columns, f"缺少必需字段: {field}"
        
        # 验证数据排序（最新数据在第一行）
        assert df.iloc[0]['datetime'] >= df.iloc[1]['datetime'], "数据应按时间倒序排列"
    
    def test_get_weekly(self):
        """
        测试获取周线数据
        
        验证：
            - 返回DataFrame非空
            - 字段完整性
        """
        df = self.bars.get_weekly(self.test_code, n=10)
        
        assert not df.empty, "周线数据不应为空"
        assert 'stock_code' in df.columns, "缺少stock_code字段"
    
    def test_get_monthly(self):
        """
        测试获取月线数据
        
        验证：
            - 返回DataFrame非空
            - 字段完整性
        """
        df = self.bars.get_monthly(self.test_code, n=10)
        
        assert not df.empty, "月线数据不应为空"
        assert 'stock_code' in df.columns, "缺少stock_code字段"
    
    def test_get_latest(self):
        """
        测试获取最新一根K线
        
        验证：
            - 返回DataFrame只有1行
            - 字段完整性
        """
        df = self.bars.get_latest(self.test_code)
        
        assert len(df) == 1, "最新K线应该只有1行数据"
        assert not df.empty, "最新K线数据不应为空"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])