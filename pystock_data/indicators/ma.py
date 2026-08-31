"""
均线指标计算模块

功能：
- 计算多条均线（MA5、MA10、MA20等）
- 输入基础DataFrame，输出增强DataFrame
- 使用标准算法计算均线

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pandas as pd
from typing import List
from .base import IndicatorBase
from .tdx import MA as tdx_MA


class MAIndicator(IndicatorBase):
    """
    均线指标计算类
    
    功能：
        - 计算多条均线（MA5、MA10、MA20、MA60等）
        - 输入基础DataFrame，输出增强DataFrame
    
    使用示例：
        >>> ma = MAIndicator()
        >>> ma_df = ma.calculate(basic_df)
    
    参数说明：
        periods: 均线周期列表，默认[5, 10, 20, 60]
    
    返回字段：
        ma5: 5日均线
        ma10: 10日均线
        ma20: 20日均线
        ma60: 60日均线
    
    注意：
        - 输入DataFrame必须包含close字段
        - 均线指标用于判断趋势方向和支撑阻力位
    """
    
    def __init__(self, periods: List[int] = None):
        """
        初始化均线指标
        
        Args:
            periods (List[int], optional): 均线周期列表，默认为[5, 10, 20, 60]
        """
        super().__init__(name='MA', required_fields=['close'])
        self.periods = periods or [5, 10, 20, 60]
    
    def calculate(self, df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """
        计算均线指标
        
        Args:
            df (DataFrame): 基础数据，必须包含close字段
            periods (List[int], optional): 均线周期列表
                None - 使用初始化时设置的periods（默认[5, 10, 20, 60]）
                List[int] - 使用运行时传入的自定义周期列表
        
        Returns:
            DataFrame: 增强数据（基础字段 + ma字段）
        
        Raises:
            ValueError: 如果输入DataFrame缺少必需字段或periods参数不合法
        
        Example:
            # 使用默认周期
            >>> ma = MAIndicator()
            >>> ma_df = ma.calculate(basic_df)  # 使用[5, 10, 20, 60]
            
            # 使用初始化自定义周期
            >>> ma = MAIndicator(periods=[5, 7, 20])
            >>> ma_df = ma.calculate(basic_df)  # 使用[5, 7, 20]
            
            # 运行时动态指定周期
            >>> ma = MAIndicator()
            >>> df1 = ma.calculate(basic_df, periods=[3, 5, 7])  # 临时使用[3, 5, 7]
            >>> df2 = ma.calculate(basic_df)  # 仍使用默认[5, 10, 20, 60]
        
        Note:
            - periods参数支持运行时动态传入，无需重新创建实例
            - 每次调用可以使用不同的周期组合
            - 向后兼容：periods=None时使用初始化设置的周期
        """
        # 验证输入DataFrame
        if not self.validate_input(df):
            return df.copy()
        
        # 确定使用的周期参数
        use_periods = periods if periods is not None else self.periods
        
        # 验证周期参数
        self._validate_periods(use_periods)
        
        # 复制DataFrame避免修改原数据
        df = df.copy()
        
        # 计算各周期均线
        for period in use_periods:
            # 公式来源：tdx 公式函数库 MA（标准滚动均值，前 N-1 行为 NaN）
            ma = pd.Series(tdx_MA(df['close'].values, period), index=df.index)
            # 前 period-1 行用部分窗口均值补齐（保持历史行为：min_periods=1）
            ma = ma.fillna(df['close'].expanding().mean())
            # 均线字段名：ma5, ma10, ma20, ma60等
            field_name = f'ma{period}'
            # 保留两位小数
            df[field_name] = ma.round(2)
        
        return df
    
    def get_periods(self) -> List[int]:
        """
        获取均线周期列表
        
        Returns:
            List[int]: 均线周期列表
        
        Example:
            >>> ma = MAIndicator()
            >>> periods = ma.get_periods()
        """
        return self.periods