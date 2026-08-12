# PyStock数据层项目规范

## 1. 项目概述

### 1.1 项目定位
PyStock数据层是一个专注于股票数据获取和技术指标计算的Python数据层。

### 1.2 核心特点
- **分层架构**：基础数据层 + 指标数据层
- **统一输出**：所有数据返回标准DataFrame
- **易于扩展**：模块化设计，新增功能简单

### 1.3 适用范围
- 量化交易策略开发
- 股票数据分析应用
- 技术指标计算服务

---

## 2. 架构设计

### 2.1 三层架构
```
┌─────────────────────────────────┐
│      指标数据层      │
│  KDJ、MACD、MA等技术指标         │
│  输入：基础DataFrame              │
│  输出：增强DataFrame（含指标字段）│
└─────────────────────────────────┘
              ↓ 基于基础数据计算
┌─────────────────────────────────┐
│      基础数据层     │
│  日线、周线、月线、分时数据        │
│  字段：datetime、open、close...  │
│  输出：标准DataFrame              │
└─────────────────────────────────┘
              ↓ 获取原始数据
┌─────────────────────────────────┐
│      数据源层        │
│  通达信数据源封装                │
└─────────────────────────────────┘
```

### 2.2 模块职责

#### 数据源层（Source Layer）
- **职责**：封装外部数据源（通达信）
- **位置**：`pystock_data/source/`
- **输出**：原始DataFrame（待标准化）
- **特点**：数据获取、异常处理

#### 基础数据层（Basic Layer）
- **职责**：提供标准化的基础行情数据
- **位置**：`pystock_data/basic/`
- **输出**：标准基础DataFrame
- **特点**：字段统一、格式标准、易于使用

#### 指标数据层（Indicator Layer）
- **职责**：基于基础数据计算技术指标
- **位置**：`pystock_data/indicators/`
- **输出**：增强DataFrame（基础字段 + 指标字段）
- **特点**：数据增强、易组合、可扩展

### 2.3 数据流转
```
数据源 → 基础DataFrame → 指标DataFrame → 应用
```

---

## 3. 命名规范

### 3.1 文件命名规范

#### Python文件命名
- **格式**：小写字母 + 下划线（snake_case）
- **规则**：功能清晰，避免缩写
- **示例**：
  - `tdx_source.py` - 通达信数据源
  - `basic_bars.py` - 基础K线数据
  - `kdj_indicator.py` - KDJ指标
  - `volume_ratio.py` - 量比指标

#### 测试文件命名
- **格式**：`test_` + 功能名 + `.py`
- **示例**：
  - `test_basic_bars.py` - 测试基础K线
  - `test_kdj_indicator.py` - 测试KDJ指标

#### 文档文件命名
- **格式**：大写字母 + 下划线 + `.md`
- **示例**：
  - `PROJECT_STANDARDS.md` - 项目规范
  - `ARCHITECTURE.md` - 架构设计

#### 目录命名
- **格式**：小写字母（单个单词优先）
- **示例**：
  - `source/` - 数据源
  - `basic/` - 基础数据
  - `indicators/` - 指标
  - `tests/` - 测试

---

### 3.2 类命名规范

#### 基础命名规则
- **格式**：驼峰命名（PascalCase）
- **规则**：功能名 + 层级后缀

#### 数据源类命名
- **格式**：`数据源类型` + `Source`
- **示例**：
  - `TdxSource` - 通达信数据源
  - `WebSource` - Web数据源
  - `ApiSource` - API数据源

#### 基础数据类命名
- **格式**：`Basic` + `数据类型` + `s`（复数）
- **示例**：
  - `BasicBars` - 基础K线数据
  - `BasicMinutes` - 基础分时数据
  - `BasicRealtime` - 基础实时数据

#### 指标类命名
- **格式**：`指标名称` + `Indicator`
- **示例**：
  - `KDJIndicator` - KDJ指标
  - `MACDIndicator` - MACD指标
  - `MAIndicator` - 均线指标
  - `VolumeRatioIndicator` - 量比指标

#### 基类/抽象类命名
- **格式**：`功能描述` + `Base`
- **示例**：
  - `IndicatorBase` - 指标基类
  - `SourceBase` - 数据源基类

---

### 3.3 方法命名规范

#### 数据获取方法
- **格式**：`get_` + `数据类型` + `_` + `频率`（可选）
- **示例**：
  - `get_daily()` - 获取日线
  - `get_weekly()` - 获取周线
  - `get_monthly()` - 获取月线
  - `get_data()` - 获取数据（通用）

#### 指标计算方法
- **格式**：统一使用 `calculate()`
- **示例**：
  - `kdj.calculate(df)` - 计算KDJ
  - `macd.calculate(df)` - 计算MACD

#### 工具方法
- **格式**：`动词` + `名词` + `()` + 下划线分隔
- **示例**：
  - `standardize_fields()` - 标准化字段
  - `validate_input()` - 验证输入
  - `transform_data()` - 转换数据

#### 私有方法
- **格式**：`_` + 方法名
- **示例**：
  - `_validate_input()` - 私有验证方法
  - `_fetch_raw_data()` - 私有获取方法

---

### 3.4 变量命名规范

#### 普通变量
- **格式**：小写字母 + 下划线
- **示例**：
  - `stock_code` - 股票代码
  - `bar_data` - K线数据
  - `date_str` - 日期字符串

#### 常量
- **格式**：全大写 + 下划线
- **示例**：
  - `DEFAULT_OFFSET` - 默认偏移量
  - `FIELD_MAPPING` - 字段映射
  - `MAX_CACHE_SIZE` - 最大缓存大小

#### DataFrame变量
- **格式**：功能描述 + `_df`（后缀）
- **示例**：
  - `basic_df` - 基础DataFrame
  - `kdj_df` - KDJ DataFrame
  - `minute_df` - 分时DataFrame
  - `enhanced_df` - 增强DataFrame

#### 参数变量
- **格式**：简短清晰的名称
- **示例**：
  - `code` - 股票代码
  - `n` - 数量
  - `date` - 日期
  - `offset` - 偏移量

---

### 3.5 数据字段命名规范

#### 基础字段（标准命名）
```python
'stock_code'      # 股票代码（新增）
'datetime'        # 时间戳
'trade_date'      # 交易日期（YYYY-MM-DD）
'open'            # 开盘价
'close'           # 收盘价
'high'            # 最高价
'low'             # 最低价
'volume'          # 成交量（统一用volume，不用vol）
'amount'          # 成交额
```

#### 分时数据额外字段
```python
'hour'            # 小时
'minute'          # 分钟
'time_index'      # 时间序号
```

#### 指标字段（标准前缀）
```python
# KDJ指标
'kdj_k'           # K值
'kdj_d'           # D值
'kdj_j'           # J值

# MACD指标
'macd_dif'        # DIF线
'macd_dea'        # DEA线
'macd_macd'       # MACD柱

# 均线指标
'ma5'             # 5日均线
'ma10'            # 10日均线
'ma20'            # 20日均线
'ma60'            # 60日均线

# 量比指标
'volume_ratio'    # 量比
'cum_volume'      # 累计成交量
'avg_volume'      # 平均成交量
```

---

## 4. 代码规范

### 4.1 PEP8规范
- 遵循Python官方PEP8代码风格
- 每行最大长度：79字符
- 使用4个空格缩进（不用Tab）
- 函数间空2行，类间空2行
- 导入间空1行

### 4.2 导入顺序
```python
# 1. 标准库导入
import pandas as pd
from abc import ABC, abstractmethod
from typing import DataFrame, Dict, List

# 2. 第三方库导入
from mootdx.quotes import Quotes
import numpy as np

# 3. 本地模块导入（相对导入）
from .base import IndicatorBase
from ..source.utils import standardize_fields
```

### 4.3 注释规范

#### 文件注释
```python
"""
模块描述：简短说明模块功能

详细描述：
- 主要功能1：功能说明
- 主要功能2：功能说明

作者：作者名
日期：创建日期
版本：1.0.0
"""
```

#### 类注释
```python
class KDJIndicator:
    """
    KDJ指标计算类
    
    功能：
    - 计算K、D、J三个指标值
    - 输入基础DataFrame，输出增强DataFrame
    
    使用示例：
        kdj = KDJIndicator()
        kdj_df = kdj.calculate(basic_df)
    
    参数说明：
        n: 周期参数，默认9
        m1: K值平滑周期，默认3
        m2: D值平滑周期，默认3
    """
```

#### 方法注释
```python
def calculate(self, df: DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> DataFrame:
    """
    计算KDJ指标
    
    参数：
        df (DataFrame): 基础数据，必须包含high、low、close字段
        n (int): 周期，默认9
        m1 (int): K值平滑周期，默认3
        m2 (int): D值平滑周期，默认3
    
    返回：
        DataFrame: 增强数据（基础字段 + kdj_k, kdj_d, kdj_j）
    
    示例：
        >>> kdj = KDJIndicator()
        >>> kdj_df = kdj.calculate(basic_df, n=9)
    
    注意：
        - 输入DataFrame必须包含基础字段
        - 输出DataFrame保留所有基础字段
    """
```

### 4.4 类型注解
```python
from typing import DataFrame, Dict, List, Optional

def get_daily(self, code: str, n: int = 100) -> DataFrame:
    """获取日线数据"""

def calculate(self, df: DataFrame) -> DataFrame:
    """计算指标"""

def get_realtime(self, codes: List[str]) -> DataFrame:
    """批量获取实时数据"""

def validate_input(self, df: DataFrame) -> Optional[str]:
    """验证输入，返回错误信息或None"""
```

---

## 5. 数据规范

### 5.1 DataFrame字段顺序
```python
# 基础DataFrame字段顺序
['stock_code', 'datetime', 'trade_date', 'open', 'close', 
 'high', 'low', 'volume', 'amount']

# 指标DataFrame字段顺序
# 基础字段在前，指标字段在后
['stock_code', 'datetime', 'trade_date', 'open', 'close', 
 'high', 'low', 'volume', 'amount', 
 'kdj_k', 'kdj_d', 'kdj_j']  # 指标字段追加在后面
```

### 5.2 数据类型定义
```python
# 字段数据类型标准
stock_code: str              # 股票代码（6位字符串）
datetime: datetime           # 时间戳（datetime类型）
trade_date: str              # 日期字符串（YYYY-MM-DD）
open: float                  # 开盘价（浮点数）
close: float                 # 收盘价（浮点数）
high: float                  # 最高价（浮点数）
low: float                   # 最低价（浮点数）
volume: int                  # 成交量（整数）
amount: float                # 成交额（浮点数）
```

### 5.3 数据排序规则
```python
# K线数据排序：最新数据在第一行（index=0）
df = df.sort_values('datetime', ascending=False).reset_index(drop=True)

# 分时数据排序：从9:30到14:59（时间正序）
df = df.sort_values('datetime', ascending=True).reset_index(drop=True)
```

### 5.4 数据验证规则
```python
# 基础数据必须包含的字段
REQUIRED_FIELDS = ['stock_code', 'datetime', 'open', 'close', 'high', 'low', 'volume']

# K线数据验证
def validate_bar_data(df: DataFrame) -> bool:
    """验证K线数据完整性"""
    return all(field in df.columns for field in REQUIRED_FIELDS)

# 分时数据验证
def validate_minute_data(df: DataFrame) -> bool:
    """验证分时数据完整性"""
    required = REQUIRED_FIELDS + ['hour', 'minute']
    return all(field in df.columns for field in required)
```

---

## 6. 目录结构规范

### 6.1 标准目录结构
```
newproject/
├── PROJECT_STANDARDS.md       # 项目规范文档
├── README.md                  # 项目说明文档
│
├── docs/                      # 文档目录
│   ├── architecture.md        # 架构设计详解
│   ├── naming_guide.md        # 命名规范指南
│   ├── code_style.md          # 代码风格指南
│   └── api_reference.md       # API参考文档
│
├── examples/                  # 示例代码目录
│   ├── README.md              # 示例说明文档
│   ├── quick_test.py          # 快速功能演示
│   └── strategy_demo.py       # 策略演示（扩展）
│
└── pystock_data/              # 数据层主包
    ├── __init__.py            # 包初始化，导出主要类
    │
    ├── source/                # 数据源层
    │   ├── __init__.py
    │   ├── client_manager.py  # 客户端管理器（性能优化）
    │   ├── tdx_source.py      # 通达信数据源
    │   ├── web_source.py      # Web数据源（扩展）
    │   └── utils.py           # 数据源工具
    │
    ├── basic/                 # 基础数据层
    │   ├── __init__.py
    │   ├── bars.py            # K线基础数据
    │   ├── minutes.py         # 分时基础数据
    │   └── realtime.py        # 实时基础数据（扩展）
    │
    ├── indicators/            # 指标数据层
    │   ├── __init__.py
    │   ├── base.py            # 指标基类
    │   ├── kdj.py             # KDJ指标
    │   ├── macd.py            # MACD指标
    │   ├── ma.py              # 均线指标
    │   ├── volume_ratio.py    # 量比指标
    │   └── custom.py          # 自定义指标（扩展）
    │
    └── tests/                 # 测试模块
        ├── __init__.py
        ├── test_source.py     # 数据源测试
        ├── test_basic.py      # 基础数据测试
        └── test_indicators.py # 指标测试
```

### 6.2 模块划分原则
- 每个目录对应一个功能层级
- 每个文件职责单一，功能清晰
- `__init__.py` 必须导出主要类
- 测试文件与源文件对应

---

## 7. 测试规范

### 7.1 测试文件命名
- **格式**：`test_` + 功能模块名 + `.py`
- **示例**：
  - `test_basic_bars.py` - 测试基础K线
  - `test_kdj_indicator.py` - 测试KDJ指标
  - `test_source.py` - 测试数据源

### 7.2 测试覆盖率要求
- **基础数据层**：覆盖率 > 80%
- **指标数据层**：覆盖率 > 90%
- **数据源层**：覆盖率 > 70%

### 7.3 测试用例组织
```python
import pytest
from pystock_data.indicators.kdj import KDJIndicator
from pystock_data.basic.bars import BasicBars

class TestKDJIndicator:
    """KDJ指标测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.kdj = KDJIndicator()
        self.bars = BasicBars()
        self.basic_df = self.bars.get_daily('000400', 100)
    
    def test_calculate_basic(self):
        """测试基础计算功能"""
        result = self.kdj.calculate(self.basic_df)
        assert 'kdj_k' in result.columns
        assert 'kdj_d' in result.columns
        assert 'kdj_j' in result.columns
    
    def test_calculate_with_params(self):
        """测试参数变化"""
        result = self.kdj.calculate(self.basic_df, n=14, m1=3, m2=3)
        assert len(result) == len(self.basic_df)
    
    def test_validate_input(self):
        """测试输入验证"""
        # 测试缺少字段的DataFrame
        invalid_df = self.basic_df.drop(columns=['high', 'low'])
        with pytest.raises(ValueError):
            self.kdj.calculate(invalid_df)
    
    def test_output_format(self):
        """测试输出格式"""
        result = self.kdj.calculate(self.basic_df)
        # 验证基础字段仍然存在
        assert 'open' in result.columns
        assert 'close' in result.columns
```

---

## 8. 文档规范

### 8.1 README.md结构
```markdown
# 项目名称

## 项目简介
- 功能概述
- 核心特点

## 快速开始
### 安装
### 基础使用示例

## 主要功能
### 基础数据层
### 指标数据层

## API文档
### 主要类说明
### 方法说明

## 示例代码
### 基础示例
### 进阶示例

## 贡献指南
### 开发流程
### 提交规范

## 许可证
```

### 8.2 API文档格式
```markdown
## 类名

### 功能描述
简短说明类的功能

### 使用示例
```python
# 使用示例代码
```

### 方法列表

#### 方法名
**功能**：方法功能描述

**参数**：
- `param1` (类型): 参数说明
- `param2` (类型): 参数说明

**返回**：
- 返回值类型: 返回值说明

**示例**：
```python
# 使用示例代码
```

**注意**：
- 注意事项1
- 注意事项2
```

---

## 9. 扩展规范

### 9.1 新增数据源
```python
from pystock_data.source.base import SourceBase

class WebSource(SourceBase):
    """Web数据源"""
    
    def fetch_bars(self, code: str, freq: int, offset: int) -> DataFrame:
        """获取K线数据"""
        # 实现获取逻辑
        pass
        
    def fetch_minutes(self, code: str, date: str) -> DataFrame:
        """获取分时数据"""
        # 实现获取逻辑
        pass
```

### 9.2 新增指标
```python
from pystock_data.indicators.base import IndicatorBase

class CustomIndicator(IndicatorBase):
    """自定义指标"""
    
    def calculate(self, df: DataFrame) -> DataFrame:
        """计算自定义指标"""
        self._validate_input(df)
        
        # 计算逻辑
        df['custom_field'] = ...
        
        return df  # 返回增强DataFrame
```

### 9.3 新增基础数据类型
```python
from pystock_data.source.tdx_source import TdxSource

class BasicRealtime:
    """基础实时数据"""
    
    def __init__(self):
        self.source = TdxSource()
    
    def get_quote(self, code: str) -> DataFrame:
        """获取实时行情"""
        # 实现获取逻辑
        pass
```

---

## 10. 版本管理规范

### 10.1 版本号规则
- **格式**：`主版本.次版本.修订号`（如 1.0.0）
- **规则**：
  - 主版本：重大架构变更或不兼容更新
  - 欉版本：新增功能，保持兼容性
  - 修订号：Bug修复或小改进

### 10.2 Git提交规范
- **格式**：`类型: 简短描述`
- **类型**：
  - `feat`: 新功能
  - `fix`: Bug修复
  - `docs`: 文档更新
  - `refactor`: 重构
  - `test`: 测试
  - `style`: 代码风格调整
- **示例**：
  - `feat: 新增MACD指标`
  - `fix: 修复KDJ计算错误`
  - `docs: 更新API文档`

---

## 11. 附录

### 11.1 关键术语表
| 术语 | 说明 |
|------|------|
| 基础数据层 | 提供原始行情数据的层级 |
| 指标数据层 | 计算技术指标的层级 |
| DataFrame增强 | 添加新字段但保留原字段 |
| 标准字段 | 统一命名的基础字段 |

### 11.2 参考资料
- Python PEP8规范：https://www.python.org/dev/peps/pep-0008/
- pandas官方文档：https://pandas.pydata.org/
- mootdx库文档：https://github.com/mootdx/mootdx

---

**文档版本**：1.0.0  
**最后更新**：2026-06-26  
**维护者**：PyStock项目组