"""
KDJ指标测试模块

功能：
- 测试KDJIndicator类的指标计算功能
- 测试输入验证
- 测试输出字段完整性

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pytest
import pandas as pd
import numpy as np
from ..indicators import KDJIndicator


class TestKDJIndicator:
    """
    KDJIndicator测试类
    
    测试范围：
        - KDJ计算功能
        - 输入验证
        - 输出字段完整性
        - 指标值范围合理性
    """
    
    def setup_method(self):
        """
        测试初始化
        
        创建KDJIndicator实例和测试数据
        """
        self.kdj = KDJIndicator()
        
        # 创建测试DataFrame（包含必需字段）
        self.test_df = pd.DataFrame({
            'stock_code': ['000400'] * 10,
            'datetime': pd.date_range('2026-06-15', periods=10),
            'close': [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 14.0, 13.0, 12.0, 11.0],
            'high': [11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 15.0, 14.0, 13.0, 12.0],
            'low': [9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 13.0, 12.0, 11.0, 10.0]
        })
    
    def test_calculate(self):
        """
        测试KDJ计算
        
        验证：
            - 返回DataFrame非空
            - kdj_k, kdj_d, kdj_j字段存在
        """
        result_df = self.kdj.calculate(self.test_df)
        
        # 验证DataFrame非空
        assert not result_df.empty, "KDJ计算结果不应为空"
        
        # 验证KDJ字段存在
        kdj_fields = ['kdj_k', 'kdj_d', 'kdj_j']
        for field in kdj_fields:
            assert field in result_df.columns, f"缺少KDJ字段: {field}"
    
    def test_validate_input(self):
        """
        测试输入验证
        
        验证：
            - 正确输入返回True
            - 缺少必需字段返回False
        """
        # 正确输入
        assert self.kdj.validate_input(self.test_df), "有效输入应返回True"
        
        # 缺少必需字段
        invalid_df = pd.DataFrame({'close': [10.0, 11.0]})
        assert not self.kdj.validate_input(invalid_df), "无效输入应返回False"
    
    def test_indicator_values(self):
        """
        测试指标值合理性
        
        验证：
            - K、D值在0-100范围内
            - J值可能超出范围
        """
        result_df = self.kdj.calculate(self.test_df)
        
        # 验证K、D值在0-100范围内（有容错）
        assert result_df['kdj_k'].between(0, 100).mean() >= 0.8, "K值应在0-100范围内"
        assert result_df['kdj_d'].between(0, 100).mean() >= 0.8, "D值应在0-100范围内"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])