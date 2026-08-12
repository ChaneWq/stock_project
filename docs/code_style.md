# PyStock数据层代码风格指南

## 1. 代码风格概述

### 1.1 核心原则
- **可读性优先**：代码应易于阅读和理解
- **一致性**：整个项目保持统一的代码风格
- **简洁性**：避免复杂的代码结构，保持简洁
- **规范性**：严格遵循PEP8规范和Python最佳实践

### 1.2 规范基础
- 主规范：Python PEP8官方规范
- 类型注解：Python Type Hints（PEP 484）
- 文档字符串：Google风格或NumPy风格
- 代码格式化：使用Black或遵循PEP8格式

---

## 2. PEP8核心规范

### 2.1 行长度与缩进
#### 规则
- 每行最大长度：79字符
- 使用4个空格缩进（不使用Tab）
- 续行使用括号或反斜杠

#### 示例
```python
# ✅ 正确：控制行长度
def get_daily(self, code: str, n: int = 100) -> DataFrame:
    """获取日线数据"""

# ✅ 正确：续行使用括号
result = some_function(
    param1, param2, param3,
    param4, param5
)

# ❌ 错误：行过长
def get_daily_data_with_many_parameters(self, code, n, start_date, end_date, frequency):
    pass

# ❌ 错误：使用Tab缩进
def calculate():
	pass  # 使用了Tab
```

### 2.2 空行使用
#### 规则
- 类之间：2个空行
- 函数之间：2个空行
- 类内方法之间：1个空行
- 函数内逻辑块：适当空行

#### 示例
```python
# ✅ 正确：空行规范
class BasicBars:
    """基础K线数据类"""
    
    def get_daily(self, code, n):
        """获取日线"""
        pass
    
    def get_weekly(self, code, n):
        """获取周线"""
        pass


class BasicMinutes:
    """基础分时数据类"""
    
    def get_data(self, code, date):
        """获取分时数据"""
        pass


# ❌ 错误：空行过多
class BasicBars:
    
    """基础K线数据类"""
    
    
    def get_daily(self, code, n):
        
        """获取日线"""
        
        pass
```

---

## 3. 导入规范

### 3.1 导入顺序
#### 规则
1. 标准库导入
2. 第三方库导入
3. 本地模块导入
4. 每组之间空1行
5. 每组内按字母顺序排列

#### 示例
```python
# ✅ 正确：导入顺序规范
# 标准库
import os
import sys
from abc import ABC, abstractmethod
from typing import DataFrame, Dict, List, Optional

# 第三方库
import numpy as np
import pandas as pd
from mootdx.quotes import Quotes

# 本地模块
from .base import IndicatorBase
from ..source.utils import standardize_fields


# ❌ 错误：导入顺序混乱
import pandas as pd
import os
from mootdx.quotes import Quotes
import sys
from .base import IndicatorBase
from abc import ABC
```

### 3.2 导入方式
#### 规则
- 优先使用绝对导入
- 避免使用 `import *`
- 明确导入需要的类或函数

#### 示例
```python
# ✅ 正确：绝对导入
from pystock_data.indicators.kdj import KDJIndicator
from pystock_data.basic.bars import BasicBars

# ✅ 正确：相对导入（本地模块）
from .base import IndicatorBase
from ..source.utils import standardize_fields

# ❌ 错误：使用import *
from pandas import *

# ❌ 错误：导入整个模块（应该明确导入）
import pystock_data.indicators.kdj  # 应该导入具体类
```

---

## 4. 注释与文档字符串

### 4.1 文件注释
#### 规则
- 模块级注释放在文件开头
- 包含模块功能、作者、版本等信息

#### 示例
```python
"""
基础K线数据模块

功能：
- 提供日线、周线、月线等基础数据获取功能
- 标准化数据字段命名和格式
- 提供统一的数据访问接口

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pandas as pd
```

### 4.2 类文档字符串
#### 规则
- 使用三引号文档字符串
- 包含类功能、使用示例、参数说明
- 采用Google风格或NumPy风格

#### Google风格示例
```python
class KDJIndicator:
    """KDJ指标计算类。
    
    功能：
        - 计算K、D、J三个指标值
        - 输入基础DataFrame，输出增强DataFrame
    
    使用示例：
        >>> kdj = KDJIndicator()
        >>> kdj_df = kdj.calculate(basic_df)
    
    参数说明：
        n: 周期参数，默认9
        m1: K值平滑周期，默认3
        m2: D值平滑周期，默认3
    
    注意：
        输入DataFrame必须包含high、low、close字段
    """
```

#### NumPy风格示例
```python
class KDJIndicator:
    """
    KDJ指标计算类
    
    功能
    -----
    计算K、D、J三个指标值，基于基础数据计算KDJ指标
    
    参数
    -----
    n : int
        周期参数，默认为9
    m1 : int
        K值平滑周期，默认为3
    m2 : int
        D值平滑周期，默认为3
    
    示例
    -----
    >>> kdj = KDJIndicator()
    >>> kdj_df = kdj.calculate(basic_df)
    
    注意
    -----
    输入DataFrame必须包含high、low、close字段
    """
```

### 4.3 方法文档字符串
#### 规则
- 每个公开方法必须有文档字符串
- 包含功能说明、参数、返回值、示例

#### Google风格示例
```python
def calculate(self, df: DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> DataFrame:
    """计算KDJ指标。
    
    Args:
        df (DataFrame): 基础数据，必须包含high、low、close字段。
        n (int, optional): 周期，默认为9。
        m1 (int, optional): K值平滑周期，默认为3。
        m2 (int, optional): D值平滑周期，默认为3。
    
    Returns:
        DataFrame: 增强数据（基础字段 + kdj_k, kdj_d, kdj_j）。
    
    Raises:
        ValueError: 如果输入DataFrame缺少必需字段。
    
    Example:
        >>> kdj = KDJIndicator()
        >>> kdj_df = kdj.calculate(basic_df, n=9)
    """
```

### 4.4 行内注释
#### 规则
- 行内注释应与代码至少空2个空格
- 注释应简洁明确
- 避免无意义的注释

#### 示例
```python
# ✅ 正确：有意义的注释
volume_ratio = cum_volume / time_index  # 计算量比

# ✅ 正确：解释复杂逻辑
if condition1 and condition2:
    # 特殊情况处理：当同时满足两个条件时
    result = special_process()

# ❌ 错误：无意义注释
x = x + 1  # 增加x的值

# ❌ 错误：注释过多
kdj_k = ...  # 计算K值  # 使用EMA算法  # 参数为m1-1
```

---

## 5. 类型注解规范

### 5.1 基础类型注解
#### 规则
- 所有公开方法必须有类型注解
- 参数和返回值都要标注类型
- 使用typing模块的类型

#### 示例
```python
from typing import DataFrame, Dict, List, Optional, Union

# ✅ 正确：完整类型注解
def get_daily(self, code: str, n: int = 100) -> DataFrame:
    """获取日线数据"""

def calculate(self, df: DataFrame, n: int = 9) -> DataFrame:
    """计算指标"""

def get_realtime(self, codes: List[str]) -> DataFrame:
    """批量获取实时数据"""

def validate_input(self, df: DataFrame) -> Optional[str]:
    """验证输入，返回错误信息或None"""

# ❌ 错误：缺少类型注解
def get_daily(self, code, n=100):
    pass

# ❌ 错误：类型注解不完整
def get_daily(self, code: str, n=100) -> DataFrame:  # n缺少类型
    pass
```

### 5.2 复杂类型注解
#### 规则
- 使用Union表示多种可能类型
- 使用Optional表示可选类型
- 使用Dict、List表示容器类型

#### 示例
```python
from typing import Dict, List, Optional, Union

# ✅ 正确：复杂类型注解
def process_data(
    data: Union[DataFrame, Dict[str, DataFrame]],
    params: Optional[Dict[str, int]] = None
) -> Union[DataFrame, List[DataFrame]]:
    """处理数据"""
    pass

def get_batch_data(
    codes: List[str],
    dates: Optional[List[str]] = None
) -> Dict[str, DataFrame]:
    """批量获取数据"""
    pass
```

---

## 6. 代码结构规范

### 6.1 函数长度
#### 规则
- 单个函数不超过50行（建议）
- 复杂逻辑拆分为多个函数
- 每个函数职责单一

#### 示例
```python
# ✅ 正确：职责单一，长度适中
def calculate(self, df: DataFrame) -> DataFrame:
    """计算指标"""
    self._validate_input(df)
    df = self._compute_indicator(df)
    df = self._clean_result(df)
    return df

def _validate_input(self, df: DataFrame):
    """验证输入"""
    pass

def _compute_indicator(self, df: DataFrame):
    """计算指标"""
    pass

# ❌ 错误：函数过长
def calculate_everything(self, df):
    """计算所有指标（函数过长）"""
    # 50行以上的代码...
    pass
```

### 6.2 类结构
#### 规则
- 类内方法顺序：__init__ → 公开方法 → 私有方法
- 每个类职责单一
- 类内方法不超过10个（建议）

#### 示例
```python
# ✅ 正确：类结构规范
class KDJIndicator:
    """KDJ指标类"""
    
    # 初始化方法
    def __init__(self, n=9, m1=3, m2=3):
        self.n = n
        self.m1 = m1
        self.m2 = m2
    
    # 公开方法
    def calculate(self, df):
        """计算指标"""
        pass
    
    # 私有方法
    def _validate_input(self, df):
        """验证输入"""
        pass
    
    def _compute_kdj(self, df):
        """计算KDJ值"""
        pass
```

---

## 7. 错误处理规范

### 7.1 异常类型
#### 规则
- 使用具体的异常类型
- 自定义异常继承Exception
- 异常名称应清晰表达错误类型

#### 示例
```python
# ✅ 正确：具体异常类型
class ValidationError(Exception):
    """验证错误"""
    pass

class SourceError(Exception):
    """数据源错误"""
    pass

def validate_input(df):
    if 'close' not in df.columns:
        raise ValidationError("缺少close字段")

# ❌ 错误：使用通用Exception
def validate_input(df):
    if 'close' not in df.columns:
        raise Exception("缺少close字段")  # 应该用具体异常
```

### 7.2 异常处理
#### 规则
- 捕获具体异常类型
- 异常处理应包含日志记录
- 避免空except块

#### 示例
```python
# ✅ 正确：具体异常处理
try:
    df = bars.get_daily('000400', 100)
except SourceError as e:
    logger.error(f"数据源错误: {e}")
    return None
except ValidationError as e:
    logger.error(f"数据验证错误: {e}")
    return None

# ❌ 错误：空except块
try:
    df = bars.get_daily('000400', 100)
except:
    pass  # 空处理

# ❌ 错误：捕获过于宽泛
try:
    df = bars.get_daily('000400', 100)
except Exception:  # 应该用具体异常
    pass
```

---

## 8. 代码质量检查

### 8.1 使用工具
- **PEP8检查**：flake8、pylint
- **类型检查**：mypy
- **代码格式化**：black、autopep8

#### 示例配置
```bash
# 使用flake8检查
flake8 pystock_data/

# 使用mypy类型检查
mypy pystock_data/

# 使用black格式化
black pystock_data/
```

### 8.2 检查规则
- 无PEP8警告或错误
- 类型检查无错误
- 代码覆盖率达标

---

## 9. 代码最佳实践

### 9.1 避免常见错误
```python
# ❌ 错误1：变量未初始化
result = calculate(df)  # calculate未定义

# ❌ 错误2：缺少异常处理
df = bars.get_daily('000400', 100)  # 可能失败

# ❌ 错误3：类型不匹配
codes = '000400'  # 应该是List[str]类型

# ✅ 正确：完整处理
try:
    df = bars.get_daily('000400', 100)
except SourceError as e:
    logger.error(f"获取数据失败: {e}")
    df = None
```

### 9.2 代码优化
```python
# ✅ 正确：使用向量化操作
df['kdj_k'] = df['close'].ewm(com=2).mean()

# ❌ 错误：使用循环
for i in range(len(df)):
    df.loc[i, 'kdj_k'] = ...

# ✅ 正确：使用内置方法
df = df.sort_values('datetime', ascending=False)

# ❌ 错误：手动实现
df = df.iloc[::-1]  # 应该用sort_values
```

---

## 10. 代码风格检查清单

### 10.1 编写代码前
- 确认遵循PEP8规范
- 确认命名规范正确
- 确认导入顺序正确

### 10.2 编写代码中
- 添加类型注解
- 编写文档字符串
- 添加必要注释

### 10.3 编写代码后
- 运行flake8检查
- 运行mypy类型检查
- 运行black格式化

---

**文档版本**：1.0.0  
**最后更新**：2026-06-26