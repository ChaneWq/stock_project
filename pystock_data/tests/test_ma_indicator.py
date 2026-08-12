"""
均线指标测试模块

功能：
- 测试MAIndicator类的指标计算功能
- 测试输入验证
- 测试输出字段完整性

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pytest
import pandas as pd
from ..indicators import MAIndicator


class TestMAIndicator:
    """
    MAIndicator测试类
    
    测试范围：
        - 均线计算功能
        - 输入验证
        - 输出字段完整性
    """
    
    def setup_method(self):
        """
        测试初始化
        
        创建MAIndicator实例和测试数据
        """
        self.ma = MAIndicator()
        
        # 创建测试DataFrame
        self.test_df = pd.DataFrame({
            'stock_code': ['000400'] * 65,
            'datetime': pd.date_range('2026-05-01', periods=65),
            'close': [10.0 + i for i in range(65)]
        })
    
    def test_calculate(self):
        """
        测试均线计算
        
        验证：
            - 返回DataFrame非空
            - ma5, ma10, ma20, ma60字段存在
        """
        result_df = self.ma.calculate(self.test_df)
        
        assert not result_df.empty, "均线计算结果不应为空"
        
        # 验证均线字段存在
        ma_fields = ['ma5', 'ma10', 'ma20', 'ma60']
        for field in ma_fields:
            assert field in result_df.columns, f"缺少均线字段: {field}"
    
    def test_get_periods(self):
        """
        测试获取均线周期
        
        验证：
            - 返回周期列表正确
        """
        periods = self.ma.get_periods()
        
        assert periods == [5, 10, 20, 60], "默认周期应为[5, 10, 20, 60]"
    
    def test_custom_periods_init(self):
        """
        测试初始化自定义周期
        
        验证：
            - 初始化时设置自定义周期生效
        """
        # 初始化自定义周期
        custom_ma = MAIndicator(periods=[3, 5, 7])
        result_df = custom_ma.calculate(self.test_df)
        
        # 验证自定义周期字段存在
        custom_fields = ['ma3', 'ma5', 'ma7']
        for field in custom_fields:
            assert field in result_df.columns, f"缺少自定义均线字段: {field}"
        
        # 验证默认周期字段不存在
        default_fields = ['ma10', 'ma20', 'ma60']
        for field in default_fields:
            assert field not in result_df.columns, f"不应存在默认均线字段: {field}"
    
    def test_dynamic_periods_runtime(self):
        """
        测试运行时动态传入周期参数
        
        验证：
            - 运行时传入periods参数生效
            - 不影响默认periods设置
        """
        # 使用默认周期计算
        default_df = self.ma.calculate(self.test_df)
        assert 'ma5' in default_df.columns
        assert 'ma10' in default_df.columns
        
        # 运行时传入自定义周期
        dynamic_df = self.ma.calculate(self.test_df, periods=[3, 7])
        assert 'ma3' in dynamic_df.columns
        assert 'ma7' in dynamic_df.columns
        assert 'ma5' not in dynamic_df.columns  # 不应存在默认周期
        
        # 再次使用默认周期，验证不影响原设置
        again_df = self.ma.calculate(self.test_df)
        assert 'ma5' in again_df.columns  # 默认周期仍可用
    
    def test_periods_validation(self):
        """
        测试periods参数验证
        
        验证：
            - 非法参数抛出ValueError
        """
        # 测试空列表
        with pytest.raises(ValueError, match="周期列表不能为空"):
            self.ma.calculate(self.test_df, periods=[])
        
        # 测试非列表类型
        with pytest.raises(ValueError, match="periods必须为列表类型"):
            self.ma.calculate(self.test_df, periods="5,10,20")
        
        # 测试负数周期
        with pytest.raises(ValueError, match="周期参数必须为正整数"):
            self.ma.calculate(self.test_df, periods=[5, -10, 20])
        
        # 测试非整数周期
        with pytest.raises(ValueError, match="周期参数必须为整数"):
            self.ma.calculate(self.test_df, periods=[5, 10.5, 20])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])