# PyStock数据层架构设计文档

## 1. 架构概述

### 1.1 设计原则
- **分层设计**：清晰的层级划分，职责分离
- **单一职责**：每个模块功能单一，易于维护
- **开放封闭**：对扩展开放，对修改封闭
- **依赖倒置**：高层依赖抽象，不依赖具体实现

### 1.2 核心架构图

```
┌──────────────────────────────────────────────────┐
│              应用层（Application Layer）            │
│         策略扫描、股价提醒、数据分析等              │
└──────────────────────────────────────────────────┘
                        ↓ 使用数据层
┌──────────────────────────────────────────────────┐
│              数据层（Data Layer）                  │
│  ┌────────────────────────────────────────────┐ │
│  │  指标数据层（Indicator Layer）              │ │
│  │  - KDJIndicator                            │ │
│  │  - MACDIndicator                           │ │
│  │  - MAIndicator                             │ │
│  │  输入：基础DataFrame                         │ │
│  │  输出：增强DataFrame（基础字段 + 指标字段）  │ │
│  └────────────────────────────────────────────┘ │
│                    ↓ 基于基础数据计算              │
│  ┌────────────────────────────────────────────┐ │
│  │  基础数据层（Basic Layer）                  │ │
│  │  - BasicBars                               │ │
│  │  - BasicMinutes（普通分时）                  │ │
│  │  - BasicMinutesWithVR（带量比分时）✨        │ │
│  │  输出：标准DataFrame                         │ │
│  └────────────────────────────────────────────┘ │
│                    ↓ 获取原始数据                  │
│  ┌────────────────────────────────────────────┐ │
│  │  数据源层（Source Layer）                   │ │
│  │  - TdxSource                               │ │
│  │  输出：原始DataFrame                         │ │
│  └────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
                        ↓ 连接外部数据源
┌──────────────────────────────────────────────────┐
│              外部数据源（External Data Sources）   │
│  - 通达信数据源（mootdx）                          │
│  - Web API数据源（扩展）                           │
└──────────────────────────────────────────────────┘
```

---

## 2. 分层详细设计

### 2.1 数据源层（Source Layer）

#### 设计目标
- 封装外部数据源，提供统一的数据获取接口
- 处理数据源异常，保证数据获取稳定性
- 提供数据格式转换功能
- **性能优化**：避免客户端重复初始化

#### 性能优化 - ClientManager

**问题分析**：
原实现中每次创建TdxSource都会初始化新client：
```python
# 问题：频繁初始化
bars1 = BasicBars()      # 初始化client1
bars2 = BasicBars()      # 初始化client2（浪费）
bars3 = BasicBars()      # 初始化client3（浪费）
```

**解决方案**：引入ClientManager统一管理client实例

```python
# ClientManager：全局客户端管理器
class ClientManager:
    """管理通达信客户端实例的创建和缓存"""
    _clients = {}  # 缓存字典：{market: client_instance}
    
    @classmethod
    def get_client(cls, market='std'):
        """获取或创建客户端（缓存复用）"""
        if market not in cls._clients:
            cls._clients[market] = Quotes.factory(market=market)
        return cls._clients[market]
```

**优化效果**：
- ✅ **避免重复初始化**：多个TdxSource共享同一个client
- ✅ **懒加载机制**：首次使用时才初始化，节省资源
- ✅ **多市场支持**：不同market有不同client实例
- ✅ **全局统一管理**：易于监控、扩展和维护

#### 核心类设计
```python
# 数据源抽象基类
class SourceBase:
    """数据源基类"""
    
    def fetch_bars(self, code, freq, offset) -> DataFrame:
        """获取K线数据"""
        raise NotImplementedError
    
    def fetch_minutes(self, code, date) -> DataFrame:
        """获取分时数据"""
        raise NotImplementedError

# 通达信数据源实现（优化后）
class TdxSource(SourceBase):
    """通达信数据源"""
    
    def __init__(self, market='std'):
        self.market = market
        # 不持有client实例，通过ClientManager获取
    
    def fetch_bars(self, code, freq, offset):
        # 通过ClientManager获取client（缓存复用）
        client = ClientManager.get_client(self.market)
        
        # 调用mootdx获取原始数据
        df = client.bars(symbol=code, frequency=freq, offset=offset)
        return df
    
    def fetch_minutes(self, code, date):
        # 通过ClientManager获取client
        client = ClientManager.get_client(self.market)
        
        # 获取分时数据
        df = client.minutes(symbol=code, date=date)
        return df
```

**使用对比**：

原实现（性能问题）：
```python
# 3次创建 = 3个client实例
bars1 = BasicBars()      # client1初始化
bars2 = BasicBars()      # client2初始化（浪费）
bars3 = BasicBars()      # client3初始化（浪费）
```

优化后（高效）：
```python
# 3次创建 = 1个client实例（共享）
bars1 = BasicBars()      # client首次初始化并缓存
bars2 = BasicBars()      # 使用缓存的client（高效）
bars3 = BasicBars()      # 使用缓存的client（高效）

# ClientManager缓存状态
assert ClientManager.get_client_count() == 1  # 只有1个client
```

#### 数据流转
```
外部数据源 → TdxSource → 原始DataFrame → BasicBars
```

---

### 2.2 基础数据层（Basic Layer）

#### 设计目标
- 提供标准化的基础行情数据
- 统一数据字段命名和格式
- 提供多种频率数据（日/周/月/分时）

#### 核心类设计
```python
# K线基础数据类
class BasicBars:
    """基础K线数据"""
    
    def __init__(self):
        self.source = TdxSource()  # 依赖数据源
    
    def get_daily(self, code, n=100) -> DataFrame:
        """获取日线数据"""
        df = self.source.fetch_bars(code, 9, n)
        return self._standardize(df)  # 标准化
    
    def get_weekly(self, code, n=100) -> DataFrame:
        """获取周线数据"""
        df = self.source.fetch_bars(code, 5, n)
        return self._standardize(df)
    
    def get_monthly(self, code, n=100) -> DataFrame:
        """获取月线数据"""
        df = self.source.fetch_bars(code, 6, n)
        return self._standardize(df)
    
    def _standardize(self, df):
        """标准化字段"""
        # 统一字段命名
        # 添加stock_code字段
        # 格式化日期字段
        return df

# 分时基础数据类（普通分时）
class BasicMinutes:
    """基础分时数据（单日）"""
    
    def __init__(self):
        self.source = TdxSource()
    
    def get_data(self, code, date) -> DataFrame:
        """获取分时数据（不包含量比）"""
        df = self.source.fetch_minutes(code, date)
        return self._standardize_minutes(df)

# 带量比的分时数据类（需要多日数据）
class BasicMinutesWithVR:
    """带量比的分时数据（自动获取过去n日数据）"""
    
    def __init__(self):
        self.source = TdxSource()
    
    def get_data(self, code, date, n=5) -> DataFrame:
        """获取带量比的分时数据"""
        # Step 1: 获取当日分时数据
        minute_df = self.source.fetch_minutes(code, date)
        # Step 2: 获取过去n日日线数据
        day_data = self.source.fetch_prev_n_day_vol(code, n, date)
        # Step 3: 计算量比
        return self._calc_volume_ratio(minute_df, day_data)
```

**设计说明**：
- **BasicMinutes**：普通分时数据，单日240分钟，轻量快速
- **BasicMinutesWithVR**：带量比分时数据，需要过去n日日线数据作为基准
- **量比不在指标层**：因为量比计算依赖多日历史数据，不适合作为单纯指标封装

#### 输出标准
```python
# 标准基础DataFrame字段
columns = [
    'stock_code',   # 股票代码
    'datetime',     # 时间戳
    'trade_date',   # 交易日期 YYYY-MM-DD
    'open',         # 开盘价
    'close',        # 收盘价
    'high',         # 最高价
    'low',          # 最低价
    'volume',       # 成交量
    'amount'        # 成交额
]
```

---

### 2.3 指标数据层（Indicator Layer）

#### 设计目标
- 基于基础数据计算技术指标
- 提供数据增强功能（添加字段）
- 支持多个指标组合使用

#### 核心类设计
```python
# 指标抽象基类
class IndicatorBase:
    """指标基类"""
    
    def calculate(self, df) -> DataFrame:
        """计算指标"""
        raise NotImplementedError
    
    def _validate_input(self, df):
        """验证输入数据"""
        # 检查必需字段是否存在
        pass

# KDJ指标实现
class KDJIndicator(IndicatorBase):
    """KDJ指标"""
    
    def calculate(self, df, n=9, m1=3, m2=3):
        """计算KDJ指标"""
        self._validate_input(df)  # 验证
        
        # 计算KDJ
        low_n = df['low'].rolling(n).min()
        high_n = df['high'].rolling(n).max()
        rsv = (df['close'] - low_n) / (high_n - low_n) * 100
        
        df['kdj_k'] = rsv.ewm(com=m1-1).mean()
        df['kdj_d'] = df['kdj_k'].ewm(com=m2-1).mean()
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']
        
        return df  # 返回增强DataFrame

# MACD指标实现
class MACDIndicator(IndicatorBase):
    """MACD指标"""
    
    def calculate(self, df, fast=12, slow=26, signal=9):
        """计算MACD指标"""
        ema_fast = df['close'].ewm(span=fast).mean()
        ema_slow = df['close'].ewm(span=slow).mean()
        
        df['macd_dif'] = ema_fast - ema_slow
        df['macd_dea'] = df['macd_dif'].ewm(span=signal).mean()
        df['macd_macd'] = 2 * (df['macd_dif'] - df['macd_dea'])
        
        return df
```

#### 数据增强机制
```
基础DataFrame（基础字段）
    ↓ 指标计算
增强DataFrame（基础字段 + 指标字段）
    ↓ 再计算其他指标
最终DataFrame（基础字段 + 多个指标字段）
```

---

## 3. 数据流转机制

### 3.1 数据获取流程
```
1. 应用调用 BasicBars.get_daily('000400', 100)
2. BasicBars 调用 TdxSource.fetch_bars('000400', 9, 100)
3. TdxSource 调用 mootdx.client.bars()
4. mootdx 返回原始DataFrame
5. TdxSource 返回原始DataFrame
6. BasicBars 标准化字段，返回标准DataFrame
7. 应用获得标准基础DataFrame
```

### 3.2 指标计算流程
```
1. 应用获得基础DataFrame
2. 应用调用 KDJIndicator.calculate(basic_df)
3. KDJIndicator验证输入数据
4. KDJIndicator计算K、D、J值
5. KDJIndicator添加字段到DataFrame
6. KDJIndicator返回增强DataFrame
7. 应用获得增强DataFrame（含KDJ字段）
```

### 3.3 多指标组合流程
```python
# 示例：组合多个指标
basic_df = bars.get_daily('000400', 100)

# 连续计算多个指标
kdj_df = kdj.calculate(basic_df)     # 添加KDJ字段
macd_df = macd.calculate(kdj_df)     # 再添加MACD字段
ma_df = ma.calculate(macd_df)        # 再添加MA字段

# 最终DataFrame包含所有指标字段
final_df = ma_df
# 字段：基础字段 + KDJ + MACD + MA
```

---

## 4. 设计模式应用

### 4.1 工厂模式
```python
# 数据源工厂
class SourceFactory:
    """数据源工厂"""
    
    @staticmethod
    def create(source_type='tdx'):
        """创建数据源实例"""
        if source_type == 'tdx':
            return TdxSource()
        elif source_type == 'web':
            return WebSource()
        else:
            raise ValueError(f"不支持的数据源: {source_type}")
```

### 4.2 策略模式
```python
# 指标计算策略
class IndicatorStrategy:
    """指标计算策略"""
    
    def __init__(self, indicator):
        self.indicator = indicator
    
    def execute(self, df):
        """执行指标计算"""
        return self.indicator.calculate(df)
```

### 4.3 装饰器模式
```python
# 数据增强装饰器
def enhance_with_kdj(df):
    """装饰器：添加KDJ字段"""
    kdj = KDJIndicator()
    return kdj.calculate(df)

def enhance_with_macd(df):
    """装饰器：添加MACD字段"""
    macd = MACDIndicator()
    return macd.calculate(df)

# 使用装饰器
enhanced_df = enhance_with_kdj(basic_df)
enhanced_df = enhance_with_macd(enhanced_df)
```

---

## 5. 扩展性设计

### 5.1 新增数据源
```python
# 继承SourceBase
class WebSource(SourceBase):
    """Web数据源"""
    
    def fetch_bars(self, code, freq, offset):
        # 实现Web API获取逻辑
        pass
    
    def fetch_minutes(self, code, date):
        # 实现Web API获取逻辑
        pass

# 注册到工厂
SourceFactory.register('web', WebSource)
```

### 5.2 新增指标
```python
# 继承IndicatorBase
class RSIIndicator(IndicatorBase):
    """RSI指标"""
    
    def calculate(self, df, period=14):
        """计算RSI指标"""
        # 计算逻辑
        df['rsi'] = ...
        return df
```

### 5.3 新增基础数据类型
```python
# 新增实时数据类
class BasicRealtime:
    """基础实时数据"""
    
    def __init__(self):
        self.source = SourceFactory.create()
    
    def get_quote(self, code):
        """获取实时行情"""
        # 实现获取逻辑
        pass
```

---

## 6. 性能优化设计

### 6.1 数据缓存机制（可选扩展）
```python
# 缓存装饰器
def cache_result(func):
    """缓存结果装饰器"""
    cache = {}
    
    def wrapper(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]
    
    return wrapper

class BasicBars:
    @cache_result
    def get_daily(self, code, n=100):
        # 获取数据
        pass
```

### 6.2 批量查询优化（可选扩展）
```python
# 批量获取数据
class BasicBars:
    def get_batch(self, codes, n=100):
        """批量获取数据"""
        results = {}
        for code in codes:
            results[code] = self.get_daily(code, n)
        return results
```

---

## 7. 异常处理机制

### 7.1 异常层级
```
数据源异常 → SourceException
数据验证异常 → ValidationException
数据处理异常 → ProcessException
```

### 7.2 异常处理示例
```python
class SourceException(Exception):
    """数据源异常"""
    pass

class ValidationException(Exception):
    """验证异常"""
    pass

# 使用示例
try:
    df = bars.get_daily('000400', 100)
except SourceException as e:
    print(f"数据源错误: {e}")
except ValidationException as e:
    print(f"数据验证错误: {e}")
```

---

## 8. 架构优势

### 8.1 分层优势
- **职责清晰**：每层功能明确，易于理解
- **易于维护**：修改一层不影响其他层
- **易于测试**：每层独立测试

### 8.2 扩展优势
- **新增数据源**：只需实现SourceBase
- **新增指标**：只需继承IndicatorBase
- **新增数据类型**：新增基础数据类

### 8.3 使用优势
- **统一接口**：所有数据使用相同接口
- **数据增强**：指标封装基础数据，易于组合
- **易于应用**：应用层使用简单清晰

---

## 9. 架构演进路线

### 9.1 当前版本（v1.0）
- 基础数据层：K线、普通分时、带量比分时
- 指标数据层：KDJ、MACD、MA
- 数据源层：通达信

### 9.2 未来扩展（v2.0）
- 基础数据层：增加实时数据、财务数据
- 指标数据层：增加更多技术指标
- 数据源层：增加Web API、数据库数据源
- 缓存层：增加数据缓存机制

### 9.3 长期演进（v3.0）
- 应用层集成：直接提供应用服务
- 分布式架构：支持分布式数据获取
- 流式数据：支持实时流式数据处理

---

**文档版本**：1.0.0  
**最后更新**：2026-06-26