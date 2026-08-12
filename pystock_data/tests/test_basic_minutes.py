"""
基础分时数据测试模块

功能：
- 测试BasicMinutes类的分时数据获取功能
- 测试数据标准化
- 测试hour和minute字段

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pytest
import pandas as pd
from ..basic import BasicMinutes


class TestBasicMinutes:
    """
    BasicMinutes测试类
    
    测试范围：
        - 分时数据获取
        - hour和minute字段
        - 数据时间正序排列
    """
    
    def setup_method(self):
        """
        测试初始化
        
        创建BasicMinutes实例
        """
        self.minutes = BasicMinutes()
        self.test_code = '000400'
        self.test_date = '20260624'
    
    def test_get_data(self):
        """
        测试获取分时数据
        
        验证：
            - 返回DataFrame非空
            - hour和minute字段存在
            - 数据时间正序排列
        """
        df = self.minutes.get_data(self.test_code, self.test_date)
        
        # 验证DataFrame非空
        assert not df.empty, "分时数据不应为空"
        
        # 验证必需字段存在
        required_fields = ['stock_code', 'datetime', 'volume', 'hour', 'minute']
        for field in required_fields:
            assert field in df.columns, f"缺少必需字段: {field}"
        
        # 验证hour和minute字段值范围
        assert df['hour'].between(9, 15).all(), "hour应在9-15范围内"
        assert df['minute'].between(0, 59).all(), "minute应在0-59范围内"
        
        # 验证数据排序（时间正序）
        if len(df) > 1:
            assert df.iloc[0]['datetime'] <= df.iloc[1]['datetime'], "数据应按时间正序排列"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])