"""
指标基类模块

功能：
- 定义指标计算的标准接口
- 提供输入数据验证
- 定义标准化的输出格式

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pandas as pd
from typing import List


class IndicatorBase:
    """
    指标基类
    
    功能：
        - 定义指标计算的标准接口
        - 提供输入数据验证
        - 所有指标类继承此基类
    
    使用示例：
        >>> class KDJIndicator(IndicatorBase):
        >>>     def calculate(self, df):
        >>>         # 实现KDJ计算逻辑
    
    参数说明：
        name: 指标名称
        required_fields: 必需的输入字段列表
    
    注意：
        - 所有指标类必须实现calculate方法
        - 输入DataFrame必须包含required_fields中的字段
    """
    
    def __init__(self, name: str, required_fields: List[str]):
        """
        初始化指标基类
        
        Args:
            name (str): 指标名称
            required_fields (List[str]): 必需的输入字段列表
        """
        self.name = name
        self.required_fields = required_fields
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算指标（子类必须实现）
        
        Args:
            df (DataFrame): 输入DataFrame
        
        Returns:
            DataFrame: 输出DataFrame（包含指标字段）
        
        Raises:
            NotImplementedError: 子类未实现此方法
        
        Example:
            >>> kdj = KDJIndicator()
            >>> kdj_df = kdj.calculate(basic_df)
        """
        raise NotImplementedError("子类必须实现calculate方法")
    
    def validate_input(self, df: pd.DataFrame) -> bool:
        """
        验证输入DataFrame
        
        Args:
            df (DataFrame): 输入DataFrame
        
        Returns:
            bool: 输入是否有效
        
        Example:
            >>> kdj = KDJIndicator()
            >>> is_valid = kdj.validate_input(df)
        """
        if df.empty:
            print(f"[{self.name}] 输入DataFrame为空")
            return False
        
        # 检查必需字段是否存在
        missing_fields = [field for field in self.required_fields if field not in df.columns]
        
        if missing_fields:
            print(f"[{self.name}] 缺少必需字段: {missing_fields}")
            return False
        
        return True
    
    def get_indicator_name(self) -> str:
        """
        获取指标名称
        
        Returns:
            str: 指标名称
        
        Example:
            >>> kdj = KDJIndicator()
            >>> name = kdj.get_indicator_name()
        """
        return self.name