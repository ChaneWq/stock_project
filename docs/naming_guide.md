# PyStock数据层命名规范指南

## 1. 命名原则

### 1.1 核心原则
- **清晰性**：名称必须清晰表达功能或含义
- **一致性**：整个项目使用统一的命名风格
- **简洁性**：避免过长的名称，但不要过度缩写
- **规范性**：遵循Python社区惯例和PEP8规范

### 1.2 命名风格对照表
| 类型 | 风格 | 示例 |
|------|------|------|
| 文件名 | snake_case | `basic_bars.py` |
| 类名 | PascalCase | `BasicBars` |
| 函数名 | snake_case | `get_daily()` |
| 变量名 | snake_case | `stock_code` |
| 常量名 | UPPER_CASE | `DEFAULT_OFFSET` |
| 私有方法 | _snake_case | `_validate_input()` |

---

## 2. 文件命名规范

### 2.1 Python文件命名
#### 规则
- 使用小写字母 + 下划线（snake_case）
- 功能清晰，避免单个单词（除非非常通用）
- 避免缩写，使用完整单词
- 文件名应能体现模块功能

#### 示例对比
```python
# ✅ 正确命名
basic_bars.py          # 基础K线数据（清晰）
kdj_indicator.py       # KDJ指标（功能明确）
volume_ratio.py        # 量比（完整单词）
tdx_source.py          # 通达信数据源（类型明确）

# ❌ 错误命名
bars.py                # 太笼统，不明确
kdj.py                 # 缺少类型标识
vol_ratio.py           # 使用缩写volume→vol
source.py              # 缺少数据源类型
```

### 2.2 测试文件命名
#### 规则
- 使用 `test_` 前缀
- 后面跟随测试的功能模块名
- 与源文件对应

#### 示例
```python
# ✅ 正确命名
test_basic_bars.py     # 测试basic_bars.py
test_kdj_indicator.py  # 测试kdj_indicator.py
test_tdx_source.py     # 测试tdx_source.py

# ❌ 错误命名
test_bars.py           # 缺少basic前缀
kdj_test.py            # 应该test_开头
```

### 2.3 文档文件命名
#### 规则
- 使用大写字母 + 下划线
- 功能清晰，易于识别

#### 示例
```python
# ✅ 正确命名
PROJECT_STANDARDS.md   # 项目规范文档
ARCHITECTURE.md        # 架构设计文档
NAMING_GUIDE.md        # 命名规范指南

# ❌ 错误命名
standards.md           # 缺少PROJECT前缀
arch.md                # 使用缩写
```

---

## 3. 类命名规范

### 3.1 类命名规则
#### 基础规则
- 使用驼峰命名（PascalCase）
- 每个单词首字母大写
- 名称应体现类的职责或功能
- 添加层级或类型后缀

#### 后缀规则
| 后缀 | 适用范围 | 示例 |
|------|---------|------|
| `Source` | 数据源类 | `TdxSource` |
| `Base` | 基类/抽象类 | `IndicatorBase` |
| `Indicator` | 指标类 | `KDJIndicator` |
| `Factory` | 工厂类 | `SourceFactory` |
| `s`（复数） | 数据类 | `BasicBars` |

### 3.2 数据源类命名
#### 规则
- 格式：`数据源类型` + `Source`
- 数据源类型应清晰明确

#### 示例对比
```python
# ✅ 正确命名
class TdxSource:              # 通达信数据源
class WebSource:              # Web数据源
class ApiSource:              # API数据源
class DatabaseSource:         # 数据库数据源

# ❌ 错误命名
class Source:                 # 缺少数据源类型
class TdxDataSource:          # 重复Data和Source
class MySource:               # 不清晰的类型名
```

### 3.3 基础数据类命名
#### 规则
- 格式：`Basic` + `数据类型` + `s`（复数）
- 数据类型应清晰表达数据含义

#### 示例对比
```python
# ✅ 正确命名
class BasicBars:              # 基础K线数据
class BasicMinutes:           # 基础分时数据
class BasicRealtimeQuotes:    # 基础实时行情

# ❌ 错误命名
class Bars:                   # 缺少Basic前缀
class BasicBar:               # 应该用复数Bars
class BasicData:              # 太笼统，不明确
class BasicStockBars:         # 冗余Stock
```

### 3.4 指标类命名
#### 规则
- 格式：`指标名称` + `Indicator`
- 指标名称应使用标准术语

#### 示例对比
```python
# ✅ 正确命名
class KDJIndicator:           # KDJ指标
class MACDIndicator:          # MACD指标
class MAIndicator:            # 均线指标
class VolumeRatioIndicator:   # 量比指标
class RSIIndicator:           # RSI指标

# ❌ 错误命名
class KDJ:                    # 缺少Indicator后缀
class KDJCalculator:          # 应该用Indicator而非Calculator
class MyIndicator:            # 不清晰的指标名
class MovingAverageIndicator: # 应该用标准术语MA
```

### 3.5 基类命名
#### 规则
- 格式：`功能描述` + `Base`
- 功能描述应简洁清晰

#### 示例对比
```python
# ✅ 正确命名
class IndicatorBase:          # 指标基类
class SourceBase:             # 数据源基类
class RepositoryBase:         # 数据访问基类

# ❌ 错误命名
class BaseIndicator:          # Base应该在后面
class Base:                   # 太笼统
class IndicatorAbstract:      # 应该用Base而非Abstract
```

---

## 4. 方法命名规范

### 4.1 方法命名规则
#### 基础规则
- 使用小写字母 + 下划线（snake_case）
- 方法名应体现功能动作
- 使用动词开头（动词 + 名词）

#### 常用动词
| 动词 | 适用场景 | 示例 |
|------|---------|------|
| `get` | 数据获取 | `get_daily()` |
| `fetch` | 从源头获取 | `fetch_bars()` |
| `calculate` | 计算指标 | `calculate()` |
| `validate` | 验证数据 | `validate_input()` |
| `transform` | 数据转换 | `transform_data()` |
| `standardize` | 标准化 | `standardize_fields()` |

### 4.2 数据获取方法命名
#### 规则
- 格式：`get_` + `数据类型` + `_` + `频率`（可选）
- 频率应使用标准术语

#### 示例对比
```python
# ✅ 正确命名
def get_daily(self, code, n):         # 获取日线
def get_weekly(self, code, n):        # 获取周线
def get_monthly(self, code, n):       # 获取月线
def get_data(self, code, date):       # 获取数据（通用）

# ❌ 错误命名
def daily(self, code, n):             # 缺少get前缀
def get_day_line(self, code, n):      # 应该用daily
def getDaily(self, code, n):          # 应该用snake_case
def fetch_daily_data(self, code, n):  # 冗余data
```

### 4.3 指标计算方法命名
#### 规则
- 指标类统一使用 `calculate()` 方法名
- 参数命名清晰简洁

#### 示例对比
```python
# ✅ 正确命名
def calculate(self, df, n=9, m1=3, m2=3):
    """计算KDJ指标"""
    pass

# ❌ 错误命名
def calc_kdj(self, df):               # 应该用calculate
def compute(self, df):                # 应该用calculate
def kdj(self, df):                    # 缺少方法动作
def calculate_kdj_value(self, df):    # 冗余value
```

### 4.4 工具方法命名
#### 规则
- 格式：`动词` + `名词` + `()` + 下划线分隔
- 功能清晰明确

#### 示例对比
```python
# ✅ 正确命名
def standardize_fields(df):           # 标准化字段
def validate_input(df):               # 验证输入
def transform_data(df):               # 转换数据
def format_datetime(dt):              # 格式化时间

# ❌ 错误命名
def standard(df):                     # 缺少fields
def check(df):                        # 缺少验证对象
def do_transform(df):                 # 冗余do前缀
def format(dt):                       # 缺少datetime
```

### 4.5 私有方法命名
#### 规则
- 使用 `_` 单下划线前缀
- 遵守snake_case风格
- 功能与公开方法命名规则相同

#### 示例对比
```python
# ✅ 正确命名
def _validate_input(self, df):        # 私有验证方法
def _fetch_raw_data(self, code):      # 私有获取方法
def _transform_internal(self, df):    # 私有转换方法

# ❌ 错误命名
def __validate_input(self, df):       # 不应使用双下划线
def validateInput(self, df):          # 应该用snake_case
def _validate(self, df):              # 缺少input对象
```

---

## 5. 变量命名规范

### 5.1 普通变量命名
#### 规则
- 使用小写字母 + 下划线（snake_case）
- 名称应清晰表达变量含义
- 避免单个字母（循环变量除外）

#### 示例对比
```python
# ✅ 正确命名
stock_code = '000400'                 # 股票代码
bar_data = df                         # K线数据
date_str = '2026-06-24'               # 日期字符串
volume_ratio = 1.5                    # 量比

# ❌ 错误命名
code = '000400'                       # 不够清晰
data = df                             # 太笼统
d = '2026-06-24'                      # 单个字母
vr = 1.5                              # 使用缩写
```

### 5.2 DataFrame变量命名
#### 规则
- 格式：功能描述 + `_df`（后缀）
- 功能描述应清晰明确

#### 示例对比
```python
# ✅ 正确命名
basic_df = bars.get_daily('000400', 100)     # 基础DataFrame
kdj_df = kdj.calculate(basic_df)             # KDJ DataFrame
minute_df = minutes.get_data('000400', date) # 分时DataFrame
enhanced_df = macd.calculate(kdj_df)         # 增强DataFrame

# ❌ 错误命名
df = bars.get_daily('000400', 100)           # 缺少功能描述
basic_data = bars.get_daily('000400', 100)   # 应该用_df后缀
kdj_dataframe = kdj.calculate(basic_df)      # 应该用_df而非_dataframe
```

### 5.3 常量命名
#### 规则
- 使用全大写字母 + 下划线
- 常量应定义在模块或类的顶部
- 名称应清晰表达常量含义

#### 示例对比
```python
# ✅ 正确命名
DEFAULT_OFFSET = 100                  # 默认偏移量
FIELD_MAPPING = {...}                 # 字段映射
MAX_CACHE_SIZE = 1000                 # 最大缓存大小
REQUIRED_FIELDS = ['open', 'close']   # 必需字段

# ❌ 错误命名
default_offset = 100                  # 应该全大写
DefaultOffset = 100                   # 应该用下划线分隔
OFFSET = 100                          # 缺少DEFAULT前缀
```

### 5.4 参数变量命名
#### 规则
- 使用简短清晰的名称
- 避免过度缩写
- 参数名应能体现参数含义

#### 示例对比
```python
# ✅ 正确命名
def get_daily(code, n=100):           # code: 股票代码, n: 数量
def calculate(df, n=9, m1=3, m2=3):   # df: DataFrame, n/m: 周期参数
def get_data(code, date):             # code: 股票代码, date: 日期

# ❌ 错误命名
def get_daily(stock_code, count=100): # 过长的参数名
def calculate(data_frame, period1=9): # 过长的参数名
def get_data(c, d):                   # 单个字母，不清晰
```

---

## 6. 数据字段命名规范

### 6.1 基础字段命名
#### 规则
- 使用小写字母 + 下划线
- 避免缩写，使用完整单词
- 字段名应清晰表达含义

#### 标准字段列表
```python
# ✅ 标准基础字段命名
{
    'stock_code': str,         # 股票代码（完整单词）
    'datetime': datetime,      # 时间戳（datetime类型）
    'trade_date': str,         # 交易日期（完整单词trade）
    'open': float,             # 开盘价（标准术语）
    'close': float,            # 收盘价（标准术语）
    'high': float,             # 最高价（标准术语）
    'low': float,              # 最低价（标准术语）
    'volume': int,             # 成交量（完整单词，不用vol）
    'amount': float            # 成交额（完整单词）
}

# ❌ 错误字段命名
{
    'code': str,               # 缺少stock前缀
    'dt': datetime,            # 使用缩写datetime→dt
    'date': str,               # 应该用trade_date
    'vol': int,                # 应该用volume
    'amt': float               # 应该用amount
}
```

### 6.2 指标字段命名
#### 规则
- 使用指标前缀 + `_` + 字段名
- 指标前缀应使用标准术语
- 字段名应清晰表达含义

#### KDJ指标字段
```python
# ✅ 正确命名
{
    'kdj_k': float,            # KDJ的K值（前缀kdj）
    'kdj_d': float,            # KDJ的D值
    'kdj_j': float             # KDJ的J值
}

# ❌ 错误命名
{
    'k': float,                # 缺少kdj前缀
    'kdj_K': float,            # 应该全小写
    'kdj_k_value': float       # 冗余value
}
```

#### MACD指标字段
```python
# ✅ 正确命名
{
    'macd_dif': float,         # MACD的DIF线
    'macd_dea': float,         # MACD的DEA线
    'macd_macd': float         # MACD柱
}

# ❌ 错误命名
{
    'dif': float,              # 缺少macd前缀
    'macd_DIF': float,         # 应该全小写
    'macd_histogram': float    # 应该用标准术语macd
}
```

#### 均线指标字段
```python
# ✅ 正确命名
{
    'ma5': float,              # 5日均线（前缀ma）
    'ma10': float,             # 10日均线
    'ma20': float,             # 20日均线
    'ma60': float              # 60日均线
}

# ❌ 错误命名
{
    'moving_average_5': float, # 应该用标准术语ma
    'MA5': float,              # 应该全小写
    'ma_5': float              # 应该用ma5而非ma_5
}
```

---

## 7. 命名常见错误

### 7.1 过度缩写错误
```python
# ❌ 错误：过度缩写
vr = volume_ratio              # 应该用完整单词
dt = datetime                  # 应该用datetime
amt = amount                   # 应该用amount

# ✅ 正确：使用完整单词
volume_ratio = ...
datetime = ...
amount = ...
```

### 7.2 命名不清晰错误
```python
# ❌ 错误：不清晰
data = df                      # 太笼统
result = calculate(df)         # 缺少功能描述
temp = df.copy()               # 缺少临时什么

# ✅ 正确：清晰明确
basic_df = df
kdj_df = calculate(df)
temp_df = df.copy()
```

### 7.3 风格不一致错误
```python
# ❌ 错误：风格不一致
def getDaily():                # 应该用snake_case
def Calculate():               # 应该用小写开头
class basic_bars:              # 应该用PascalCase

# ✅ 正确：风格一致
def get_daily():
def calculate():
class BasicBars:
```

### 7.4 冗余命名错误
```python
# ❌ 错误：冗余
stock_stock_code = '000400'    # 重复stock
data_dataframe = df            # 重复data
calculate_kdj_value = ...      # 冗余value

# ✅ 正确：简洁
stock_code = '000400'
data_df = df
kdj_value = ...
```

---

## 8. 命名最佳实践

### 8.1 文件命名最佳实践
- 一看文件名就知道模块功能
- 避免单个单词文件名（除非非常通用）
- 测试文件与源文件对应

### 8.2 类命名最佳实践
- 类名应体现类的职责
- 使用标准后缀（Source、Indicator、Base等）
- 避免冗余词汇

### 8.3 方法命名最佳实践
- 方法名应体现功能动作
- 使用标准动词（get、calculate、validate等）
- 参数名清晰简洁

### 8.4 变量命名最佳实践
- DataFrame变量使用 `_df` 后缀
- 常量使用全大写 + 下划线
- 变量名应能体现变量含义

---

**文档版本**：1.0.0  
**最后更新**：2026-06-26