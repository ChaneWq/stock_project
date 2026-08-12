"""
MACD指标测试模块

功能：
- 测试MACDIndicator类的指标计算功能
- 测试输入验证
- 测试输出字段完整性

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pytest
import pandas as pd
from ..indicators import MACDIndicator


class TestMACDIndicator:
    """
    MACDIndicator测试类
    
    测试范围：
        - MACD计算功能
        - 输入验证
        - 输出字段完整性
    """
    
    def setup_method(self):
        """
        测试初始化
        
        创建MACDIndicator实例和测试数据
        """
        self.macd = MACDIndicator()
        
        # 创建测试DataFrame
        self.test_df = pd.DataFrame({
            'stock_code': ['000400'] * 30,
            'datetime': pd.date_range('2026-06-01', periods=30),
            'close': [10.0 + i for i in range(30)]  # 递增序列
        })
    
    def test_calculate(self):
        """
        测试MACD计算
        
        验证：
            - 返回DataFrame非空
            - macd_dif, macd_dea, macd_macd字段存在
        """
        result_df = self.macd.calculate(self.test_df)
        
        assert not result_df.empty, "MACD计算结果不应为空"
        
        # 验证MACD字段存在
        macd_fields = ['macd_dif', 'macd_dea', 'macd_macd']
        for field in macd_fields:
            assert field in result_df.columns, f"缺少MACD字段: {field}"
    
    def test_validate_input(self):
        """
        测试输入验证
        
        验证：
            - 正确输入返回True
            - 缺少close字段返回False
        """
        assert self.macd.validate_input(self.test_df), "有效输入应返回True"
        
        invalid_df = pd.DataFrame({'open': [10.0]})
        assert not self.macd.validate_input(invalid_df), "无效输入应返回False"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])