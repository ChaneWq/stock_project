# PyStock数据层API使用指南

本文档提供完整的API调用示例，帮助开发者快速理解和使用数据层功能。

---

## 1. 快速开始

### 1.1 导入主模块

```python
from pystock_data import BasicBars, BasicMinutes, BasicMinutesWithVR
from pystock_data.indicators import KDJIndicator, MACDIndicator, MAIndicator
```

### 1.2 最简示例

```python
# 获取日线数据
bars = BasicBars()
df = bars.get_daily('000400', 100)  # 获取000400最近100根日线

print(df.head())
```

---

## 2. 基础数据层（Basic Layer）

### 2.1 BasicBars - K线数据

#### 获取日线数据

```python
from pystock_data import BasicBars

bars = BasicBars()

# 获取日线数据（最近100根）
day_df = bars.get_daily('000400', 100)

# 获取日线数据（最近50根）
day_df = bars.get_daily('000001', 50)

# 返回字段：
# - stock_code: 股票代码
# - datetime: 时间戳
# - trade_date: 交易日期（YYYY-MM-DD）
# - open: 开盘价
# - close: 收盘价
# - high: 最高价
# - low: 最低价
# - volume: 成交量
# - amount: 成交额
```

#### 获取周线数据

```python
# 获取周线数据
week_df = bars.get_weekly('000400', 50)

# 周线数据包含同样的字段
print(f"周线数据行数: {len(week_df)}")
print(week_df[['trade_date', 'close', 'volume']].head())
```

#### 获取月线数据

```python
# 获取月线数据
month_df = bars.get_monthly('000400', 30)

print(f"月线数据行数: {len(month_df)}")
print(month_df[['trade_date', 'close', 'volume']].head())
```

#### 批量获取多只股票

```python
# 批量获取多只股票日线数据
stock_codes = ['000400', '000001', '600000']
stock_data = {}

for code in stock_codes:
    bars = BasicBars()
    stock_data[code] = bars.get_daily(code, 100)
    
    print(f"{code}: {len(stock_data[code])}行数据")

# ClientManager自动优化：所有实例共享同一个client
```

---

### 2.2 BasicMinutes - 分时数据

#### 获取指定日期分时数据

```python
from pystock_data import BasicMinutes

minutes = BasicMinutes()

# 获取指定日期的分时数据（240分钟）
minute_df = minutes.get_data('000400', '20260624')

print(f"分时数据行数: {len(minute_df)}")  # 240行

# 返回字段：
# - 基础字段（同K线）
# - hour: 小时（9-15）
# - minute: 分钟（30-59）

print(minute_df[['datetime', 'close', 'volume', 'hour', 'minute']].head(10))
```

#### 分时数据时间范围

```python
# 分时数据覆盖时间范围
minute_df = minutes.get_data('000400', '20260624')

# 9:30 - 11:30 (上午120分钟)
morning_df = minute_df[minute_df['hour'] < 12]
print(f"上午分时数据: {len(morning_df)}行")

# 13:00 - 15:00 (下午120分钟)
afternoon_df = minute_df[minute_df['hour'] >= 13]
print(f"下午分时数据: {len(afternoon_df)}行")
```

---

### 2.3 BasicMinutesWithVR - 带量比的分时数据

**重要说明**：量比计算需要过去n日日线数据，因此不再作为单纯指标封装，而是作为特殊的分时数据类型。

#### 基本使用

```python
from pystock_data import BasicMinutesWithVR

# 获取带量比的分时数据（自动获取过去5日日线数据）
minutes_vr = BasicMinutesWithVR()
vr_df = minutes_vr.get_data('000400', '20260624', n=5)

# 返回240行分时数据（包含量比）
# 新增字段：
# - volume_ratio: 量比值
# - cumulative_vol: 累计成交量
# - time_index: 时间序号（1-240）
# - avg_vol_per_minute: 过去n日每分钟平均成交量

print(f"过去5日分钟均量: {minutes_vr.get_avg_vol_per_minute()}")
print(f"昨收价: {minutes_vr.get_prev_close()}")

print(vr_df[['datetime', 'volume', 'cumulative_vol', 'volume_ratio']].head(10))
```

#### 量比计算原理

```python
# 量比公式（通达信）
量比 = 累计成交量 / 时间序号 / 过去n日分钟均量

# 时间序号计算（通达信公式）
时间序号:=IF(HOUR>12,(HOUR-13)*60+MINUTE+120,(HOUR-9)*60+MINUTE-30)+1

# 验证示例：
9:30  → 1    # 开盘第一分钟
11:29 → 120  # 上午最后一分钟
13:00 → 121  # 下午第一分钟
14:59 → 240  # 收盘最后一分钟

# 量比含义：
量比 > 3  → 明显放量（异常活跃）
量比 2~3 → 放量（活跃）
量比 1~2 → 正常
量比 0.5~1 → 缩量（清淡）
量比 < 0.5 → 明显缩量（异常清淡）
```

#### 量比统计分析

```python
# 获取量比统计摘要
summary = minutes_vr.get_volume_ratio_summary(vr_df)
print(f"最大量比: {summary['max']}")
print(f"最小量比: {summary['min']}")
print(f"平均量比: {summary['avg']}")
print(f"当前量比: {summary['current']}")

# 量比趋势判断
trend = minutes_vr.get_volume_ratio_trend(vr_df, window=10)
print(f"量比趋势: {trend}")  # '上升' / '下降' / '平稳'
```

#### 量比过滤功能

```python
# 过滤放量时段（量比 >= 2.0）
high_vr = minutes_vr.filter_volume_ratio_by_range(vr_df, min_vr=2.0)
print(f"放量分钟数: {len(high_vr)}")
print(f"占比: {len(high_vr) / len(vr_df) * 100:.1f}%")

# 过滤缩量时段（量比 <= 0.8）
low_vr = minutes_vr.filter_volume_ratio_by_range(vr_df, max_vr=0.8)
print(f"缩量分钟数: {len(low_vr)}")

# 查找量比峰值时段（量比 >= 3.0）
peaks = minutes_vr.find_volume_ratio_peaks(vr_df, threshold=3.0)
for time_str, vr_value in peaks:
    print(f"{time_str}: {vr_value}")
```

#### 时段量比分析

```python
# 上午时段（9:30-11:30）
morning_vr = vr_df[vr_df['hour'] < 12]
morning_avg = morning_vr['volume_ratio'].mean()
print(f"上午平均量比: {morning_avg:.2f}")

# 下午时段（13:00-15:00）
afternoon_vr = vr_df[vr_df['hour'] >= 13]
afternoon_avg = afternoon_vr['volume_ratio'].mean()
print(f"下午平均量比: {afternoon_avg:.2f}")

# 开盘半小时（9:30-10:00）
opening_vr = vr_df[
    (vr_df['hour'] == 9) & 
    (vr_df['minute'] >= 30) & 
    (vr_df['minute'] <= 59)
]
opening_avg = opening_vr['volume_ratio'].mean()
print(f"开盘半小时平均量比: {opening_avg:.2f}")

# 收盘半小时（14:30-15:00）
closing_vr = vr_df[
    (vr_df['hour'] == 14) & 
    (vr_df['minute'] >= 30)
]
closing_avg = closing_vr['volume_ratio'].mean()
print(f"收盘半小时平均量比: {closing_avg:.2f}")
```

#### 多股票批量分析

```python
# 批量分析多只股票量比
stock_codes = ['000400', '000001', '600000']
results = []

for code in stock_codes:
    minutes_vr = BasicMinutesWithVR()
    vr_df = minutes_vr.get_data(code, '20260624', n=5)
    
    if not vr_df.empty:
        summary = minutes_vr.get_volume_ratio_summary(vr_df)
        results.append({
            'code': code,
            'avg_vr': summary['avg'],
            'max_vr': summary['max'],
            'min_vr': summary['min']
        })

# 排序分析
import pandas as pd
results_df = pd.DataFrame(results)
print("按平均量比排序:")
print(results_df.sort_values('avg_vr', ascending=False))
```

#### 对比BasicMinutes和BasicMinutesWithVR

```python
from pystock_data import BasicMinutes, BasicMinutesWithVR

# BasicMinutes：普通分时数据（单日）
minutes = BasicMinutes()
minute_df = minutes.get_data('000400', '20260624')
# 特点：快速、轻量、单日数据
# 适用：查看分时走势、简单分时分析

# BasicMinutesWithVR：带量比的分时数据（多日）
minutes_vr = BasicMinutesWithVR()
vr_df = minutes_vr.get_data('000400', '20260624', n=5)
# 特点：自动获取过去n日数据、计算量比
# 适用：分时量比分析、异常监控、活跃度判断
```

**数据依赖对比**：

| 类名 | 数据需求 | 数据源调用 | 性能 | 适用场景 |
|------|----------|-----------|------|----------|
| BasicMinutes | 当日240分钟分时 | 1次（fetch_minutes） | 快速 | 查看分时走势 |
| BasicMinutesWithVR | 当日分时 + 过去n日日线 | 2次 | 相对较慢 | 分时量比分析 |

**使用场景对比**：

| BasicMinutes适用场景 | BasicMinutesWithVR适用场景 |
|---------------------|---------------------------|
| 快速查看当日分时走势 | 分时量比分析 |
| 分时价格变动分析 | 成交量活跃度判断 |
| 不需要量比数据的场景 | 异常放量/缩量监控 |
| 实时盘中监控（仅价格） | 分时成交量对比分析 |

---

## 3. 指标数据层（Indicator Layer）

### 3.1 KDJIndicator - KDJ指标

#### 基本使用

```python
from pystock_data import BasicBars
from pystock_data.indicators import KDJIndicator

# 获取基础数据
bars = BasicBars()
basic_df = bars.get_daily('000400', 100)

# 计算KDJ指标（默认参数：n=9, m1=3, m2=3）
kdj = KDJIndicator()
kdj_df = kdj.calculate(basic_df)

# 新增字段：
# - kdj_k: K值
# - kdj_d: D值
# - kdj_j: J值

print(kdj_df[['trade_date', 'close', 'kdj_k', 'kdj_d', 'kdj_j']].head())
```

#### 自定义KDJ参数

```python
# 自定义参数计算KDJ
kdj_custom = KDJIndicator(n=14, m1=3, m2=3)
kdj_df = kdj_custom.calculate(basic_df)

print(f"自定义KDJ（n=14）:")
print(kdj_df[['kdj_k', 'kdj_d', 'kdj_j']].tail())
```

#### KDJ指标应用场景

```python
# KDJ超买超卖判断
kdj_df = kdj.calculate(basic_df)

# 超买区域：K值 > 80
overbought = kdj_df[kdj_df['kdj_k'] > 80]
print(f"超买信号: {len(overbought)}次")

# 超卖区域：K值 < 20
oversold = kdj_df[kdj_df['kdj_k'] < 20]
print(f"超卖信号: {len(oversold)}次")

# J值突破信号
breakthrough = kdj_df[kdj_df['kdj_j'] > 100]
print(f"J值突破信号: {len(breakthrough)}次")
```

---

### 3.2 MACDIndicator - MACD指标

#### 基本使用

```python
from pystock_data.indicators import MACDIndicator

# 计算MACD指标（默认参数：12, 26, 9）
macd = MACDIndicator()
macd_df = macd.calculate(basic_df)

# 新增字段：
# - macd_dif: DIF线（快线）
# - macd_dea: DEA线（慢线）
# - macd_macd: MACD柱

print(macd_df[['trade_date', 'close', 'macd_dif', 'macd_dea', 'macd_macd']].tail())
```

#### 自定义MACD参数

```python
# 自定义MACD参数
macd_custom = MACDIndicator(fast_period=6, slow_period=12, signal_period=5)
macd_df = macd_custom.calculate(basic_df)

print(f"自定义MACD（快周期6）:")
print(macd_df[['macd_dif', 'macd_dea']].head())
```

#### MACD指标应用场景

```python
# MACD金叉死叉判断
macd_df = macd.calculate(basic_df)

# 金叉：DIF上穿DEA
golden_cross = macd_df[
    (macd_df['macd_dif'] > macd_df['macd_dea']) & 
    (macd_df['macd_dif'].shift(1) <= macd_df['macd_dea'].shift(1))
]
print(f"金叉信号: {len(golden_cross)}次")

# 死叉：DIF下穿DEA
death_cross = macd_df[
    (macd_df['macd_dif'] < macd_df['macd_dea']) & 
    (macd_df['macd_dif'].shift(1) >= macd_df['macd_dea'].shift(1))
]
print(f"死叉信号: {len(death_cross)}次")

# MACD柱趋势
positive_macd = macd_df[macd_df['macd_macd'] > 0]
print(f"MACD柱正值: {len(positive_macd)}根")
```

---

### 3.3 MAIndicator - 均线指标

#### 默认周期使用

```python
from pystock_data.indicators import MAIndicator

# 默认周期：[5, 10, 20, 60]
ma = MAIndicator()
ma_df = ma.calculate(basic_df)

# 新增字段：
# - ma5: 5日均线
# - ma10: 10日均线
# - ma20: 20日均线
# - ma60: 60日均线

print(ma_df[['trade_date', 'close', 'ma5', 'ma10', 'ma20', 'ma60']].tail())
```

#### 初始化自定义周期

```python
# 初始化时设置自定义周期
ma_custom = MAIndicator(periods=[3, 5, 7])  # 短线均线
ma_df = ma_custom.calculate(basic_df)

# 新增字段：ma3, ma5, ma7
print(ma_df[['close', 'ma3', 'ma5', 'ma7']].head())

# 中线均线
ma_medium = MAIndicator(periods=[10, 20, 30])
ma_df = ma_medium.calculate(basic_df)

# 长线均线
ma_long = MAIndicator(periods=[60, 120, 250])
ma_df = ma_long.calculate(basic_df)
```

#### 运行时动态周期

```python
# 运行时动态传入周期参数
ma = MAIndicator()  # 默认周期[5, 10, 20, 60]

# 使用默认周期计算
df_default = ma.calculate(basic_df)
print(f"默认周期字段: ma5, ma10, ma20, ma60")

# 运行时临时使用不同周期
df_short = ma.calculate(basic_df, periods=[3, 5, 7])
print(f"短线周期字段: ma3, ma5, ma7")

df_long = ma.calculate(basic_df, periods=[60, 120, 250])
print(f"长线周期字段: ma60, ma120, ma250")

# 再次使用默认周期（不影响原设置）
df_again = ma.calculate(basic_df)
print(f"仍为默认周期: ma5, ma10, ma20, ma60")
```

#### 多策略均线组合

```python
# 一个实例，不同策略，不同周期
ma = MAIndicator()
basic_df = bars.get_daily('000400', 250)

# 短线策略：快周期
short_strategy = ma.calculate(basic_df, periods=[3, 5, 7])
print("短线策略均线:")
print(short_strategy[['close', 'ma3', 'ma5', 'ma7']].tail())

# 中线策略：中周期
medium_strategy = ma.calculate(basic_df, periods=[10, 20, 30])
print("中线策略均线:")
print(medium_strategy[['close', 'ma10', 'ma20', 'ma30']].tail())

# 长线策略：慢周期
long_strategy = ma.calculate(basic_df, periods=[60, 120, 250])
print("长线策略均线:")
print(long_strategy[['close', 'ma60', 'ma120', 'ma250']].tail())
```

#### 均线应用场景

```python
# 均线支撑阻力判断
ma_df = ma.calculate(basic_df)

# 价格在均线之上（多头）
above_ma5 = ma_df[ma_df['close'] > ma_df['ma5']]
print(f"价格在MA5之上: {len(above_ma5)}根")

# 均线交叉信号
ma5_cross_ma10 = ma_df[
    (ma_df['ma5'] > ma_df['ma10']) & 
    (ma_df['ma5'].shift(1) <= ma_df['ma10'].shift(1))
]
print(f"MA5上穿MA10: {len(ma5_cross_ma10)}次")
```

---

## 4. 组合使用 - 多指标组合

### 4.1 基础组合

```python
from pystock_data import BasicBars
from pystock_data.indicators import KDJIndicator, MACDIndicator, MAIndicator

# 获取基础数据
bars = BasicBars()
basic_df = bars.get_daily('000400', 100)

# 逐步添加指标
enhanced_df = basic_df.copy()

# 添加KDJ指标
kdj = KDJIndicator()
enhanced_df = kdj.calculate(enhanced_df)

# 添加MACD指标
macd = MACDIndicator()
enhanced_df = macd.calculate(enhanced_df)

# 添加均线指标
ma = MAIndicator(periods=[5, 10, 20])
enhanced_df = ma.calculate(enhanced_df)

# 最终DataFrame包含所有指标
print(f"最终字段数: {len(enhanced_df.columns)}")
print(f"所有字段: {list(enhanced_df.columns)}")
```

### 4.2 多股票批量组合

```python
# 批量获取多只股票并计算指标
stock_codes = ['000400', '000001', '600000']
stock_data = {}

for code in stock_codes:
    bars = BasicBars()
    basic_df = bars.get_daily(code, 100)
    
    # 组合多个指标
    kdj = KDJIndicator()
    macd = MACDIndicator()
    ma = MAIndicator()
    
    enhanced_df = basic_df.copy()
    enhanced_df = kdj.calculate(enhanced_df)
    enhanced_df = macd.calculate(enhanced_df)
    enhanced_df = ma.calculate(enhanced_df)
    
    stock_data[code] = enhanced_df
    
    print(f"{code} - 字段数: {len(enhanced_df.columns)}")

# ClientManager自动优化：所有实例共享client
```

### 4.3 指标组合策略分析

```python
# KDJ + MACD组合策略
kdj_df = kdj.calculate(basic_df)
kdj_macd_df = macd.calculate(kdj_df)

# KDJ超买 + MACD死叉信号
signal_df = kdj_macd_df[
    (kdj_macd_df['kdj_k'] > 80) &  # KDJ超买
    (kdj_macd_df['macd_dif'] < kdj_macd_df['macd_dea'])  # MACD死叉
]
print(f"组合信号: {len(signal_df)}次")

# 均线支撑 + KDJ超卖信号
ma_kdj_df = ma.calculate(kdj_df, periods=[5, 10])

support_signal = ma_kdj_df[
    (ma_kdj_df['close'] > ma_kdj_df['ma5']) &  # 价格在MA5之上
    (ma_kdj_df['kdj_k'] < 20)  # KDJ超卖
]
print(f"支撑+超卖信号: {len(support_signal)}次")
```

---

## 5. 数据源层（Source Layer）

### 5.1 ClientManager - 性能优化

#### 自动优化（无需手动调用）

```python
# ClientManager自动工作，无需手动调用
bars1 = BasicBars()  # client自动缓存
bars2 = BasicBars()  # 使用缓存client（高效）

# 性能优化：
# - 避免重复初始化client
# - 懒加载机制（首次使用时初始化）
# - 多实例共享同一个client
```

#### 手动查询缓存状态

```python
from pystock_data.source import ClientManager

# 查询缓存数量
count = ClientManager.get_client_count()
print(f"缓存client数量: {count}")

# 查询缓存列表
markets = ClientManager.get_cached_markets()
print(f"缓存market列表: {markets}")

# 检查是否已缓存
has_std = ClientManager.has_client('std')
print(f"std market已缓存: {has_std}")
```

#### 清空缓存（测试场景）

```python
# 清空缓存（主要用于测试）
ClientManager.clear_cache()
print(f"缓存已清空: {ClientManager.get_client_count()}")
```

---

### 5.2 TdxSource - 数据源直接调用

#### 直接使用数据源（高级用法）

```python
from pystock_data.source import TdxSource

# 创建数据源实例
source = TdxSource(market='std')

# 直接获取K线数据
df = source.fetch_bars('000400', 9, 100)  # 日线

# 直接获取分时数据
minute_df = source.fetch_minutes('000400', '20260624')

print(f"K线数据: {len(df)}行")
print(f"分时数据: {len(minute_df)}行")

# 注意：一般建议使用BasicBars/BasicMinutes，而非直接调用TdxSource
```

---

## 6. 完整应用示例

### 6.1 简单选股策略

```python
from pystock_data import BasicBars
from pystock_data.indicators import KDJIndicator, MAIndicator

def simple_stock_picker(stock_codes, n=100):
    """
    简单选股策略示例
    条件：
    1. 价格在MA5之上
    2. KDJ的K值小于30（超卖区域）
    """
    selected_stocks = []
    
    for code in stock_codes:
        # 获取数据
        bars = BasicBars()
        basic_df = bars.get_daily(code, n)
        
        # 计算指标
        kdj = KDJIndicator()
        ma = MAIndicator(periods=[5, 10])
        
        enhanced_df = basic_df.copy()
        enhanced_df = kdj.calculate(enhanced_df)
        enhanced_df = ma.calculate(enhanced_df)
        
        # 检查最新数据是否符合条件
        latest = enhanced_df.iloc[-1]
        
        if latest['close'] > latest['ma5'] and latest['kdj_k'] < 30:
            selected_stocks.append({
                'code': code,
                'close': latest['close'],
                'kdj_k': latest['kdj_k'],
                'ma5': latest['ma5']
            })
    
    return selected_stocks

# 使用示例
stock_codes = ['000400', '000001', '600000', '600519']
selected = simple_stock_picker(stock_codes)

print(f"符合条件的股票数: {len(selected)}")
for stock in selected:
    print(f"{stock['code']}: 收盘{stock['close']}, KDJ-K{stock['kdj_k']}, MA5{stock['ma5']}")
```

### 6.2 技术指标分析报告

```python
def technical_analysis_report(code, n=100):
    """
    生成技术指标分析报告
    """
    # 获取数据
    bars = BasicBars()
    basic_df = bars.get_daily(code, n)
    
    # 计算所有指标
    kdj = KDJIndicator()
    macd = MACDIndicator()
    ma = MAIndicator(periods=[5, 10, 20, 60])
    
    df = basic_df.copy()
    df = kdj.calculate(df)
    df = macd.calculate(df)
    df = ma.calculate(df)
    
    # 分析最新数据
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    # KDJ分析
    kdj_status = "超买" if latest['kdj_k'] > 80 else "超卖" if latest['kdj_k'] < 20 else "正常"
    
    # MACD分析
    macd_status = "金叉" if latest['macd_dif'] > latest['macd_dea'] else "死叉"
    
    # 均线分析
    ma_status = "多头排列" if latest['ma5'] > latest['ma10'] > latest['ma20'] else "空头排列"
    
    # 价格趋势
    price_trend = "上涨" if latest['close'] > prev['close'] else "下跌"
    
    # 生成报告
    report = {
        '股票代码': code,
        '最新价格': latest['close'],
        '价格趋势': price_trend,
        'KDJ状态': kdj_status,
        'K值': latest['kdj_k'],
        'D值': latest['kdj_d'],
        'J值': latest['kdj_j'],
        'MACD状态': macd_status,
        'DIF': latest['macd_dif'],
        'DEA': latest['macd_dea'],
        '均线状态': ma_status,
        'MA5': latest['ma5'],
        'MA10': latest['ma10'],
        'MA20': latest['ma20']
    }
    
    return report

# 使用示例
report = technical_analysis_report('000400')

print("技术指标分析报告:")
for key, value in report.items():
    print(f"{key}: {value}")
```

### 6.3 批量数据获取与分析

```python
import pandas as pd

def batch_stock_analysis(stock_codes, n=100):
    """
    批量股票分析
    """
    results = []
    
    for code in stock_codes:
        bars = BasicBars()
        basic_df = bars.get_daily(code, n)
        
        if len(basic_df) == 0:
            continue
        
        # 计算指标
        kdj = KDJIndicator()
        ma = MAIndicator(periods=[5, 10])
        
        df = basic_df.copy()
        df = kdj.calculate(df)
        df = ma.calculate(df)
        
        # 统计数据
        latest = df.iloc[-1]
        stats = {
            'code': code,
            'close': latest['close'],
            'kdj_k': latest['kdj_k'],
            'ma5': latest['ma5'],
            'volume': latest['volume']
        }
        
        results.append(stats)
    
    # 生成汇总DataFrame
    summary_df = pd.DataFrame(results)
    
    return summary_df

# 使用示例
stock_codes = ['000400', '000001', '600000', '600519', '000002']
summary = batch_stock_analysis(stock_codes)

print("批量股票分析汇总:")
print(summary)

# 排序分析
print("\n按KDJ-K值排序:")
print(summary.sort_values('kdj_k'))

print("\n按成交量排序:")
print(summary.sort_values('volume', ascending=False))
```

---

## 7. 错误处理

### 7.1 数据获取失败

```python
bars = BasicBars()

# 获取不存在的股票代码
df = bars.get_daily('999999', 100)

if len(df) == 0:
    print("股票代码不存在或数据获取失败")
else:
    print(f"数据获取成功: {len(df)}行")
```

### 7.2 指标参数验证

```python
from pystock_data.indicators import MAIndicator

ma = MAIndicator()

# 错误参数示例
try:
    df = ma.calculate(basic_df, periods=[])
except ValueError as e:
    print(f"参数错误: {e}")

try:
    df = ma.calculate(basic_df, periods="5,10,20")
except ValueError as e:
    print(f"参数错误: {e}")

try:
    df = ma.calculate(basic_df, periods=[5, -10, 20])
except ValueError as e:
    print(f"参数错误: {e}")

try:
    df = ma.calculate(basic_df, periods=[5, 10.5, 20])
except ValueError as e:
    print(f"参数错误: {e}")
```

### 7.3 DataFrame字段检查

```python
# 确保DataFrame包含必需字段
kdj = KDJIndicator()

# 错误示例：缺少必需字段
try:
    wrong_df = pd.DataFrame({'close': [10, 20, 30]})  # 缺少high、low字段
    kdj_df = kdj.calculate(wrong_df)
except ValueError as e:
    print(f"字段缺失: {e}")

# 正确做法：检查字段
def safe_calculate_indicator(df, indicator):
    """安全计算指标"""
    required_fields = indicator.required_fields
    
    if not all(field in df.columns for field in required_fields):
        missing = [f for f in required_fields if f not in df.columns]
        print(f"缺少字段: {missing}")
        return df.copy()
    
    return indicator.calculate(df)

# 使用
bars = BasicBars()
basic_df = bars.get_daily('000400', 100)

kdj_df = safe_calculate_indicator(basic_df, kdj)
```

---

## 8. 性能优化建议

### 8.1 批量处理优化

```python
# 推荐：批量处理时复用client
from pystock_data import BasicBars

# ClientManager自动优化：创建多个BasicBars实例共享client
stock_codes = ['000400', '000001', '600000']

bars_instances = [BasicBars() for _ in range(len(stock_codes))]
# 只创建1个client实例（优化后）

# 获取数据
for i, code in enumerate(stock_codes):
    df = bars_instances[i].get_daily(code, 100)
    print(f"{code}: {len(df)}行")

# 验证client缓存数量
from pystock_data.source import ClientManager
print(f"Client缓存数量: {ClientManager.get_client_count()}")  # 应为1
```

### 8.2 指标计算优化

```python
# 推荐：一次计算多个指标
bars = BasicBars()
basic_df = bars.get_daily('000400', 100)

# 一次性添加所有指标
kdj = KDJIndicator()
macd = MACDIndicator()
ma = MAIndicator()

enhanced_df = basic_df.copy()
enhanced_df = kdj.calculate(enhanced_df)
enhanced_df = macd.calculate(enhanced_df)
enhanced_df = ma.calculate(enhanced_df)

# 避免：多次重新获取基础数据
# 不推荐：
# df1 = bars.get_daily('000400', 100)
# df2 = bars.get_daily('000400', 100)  # 重复获取
```

---

## 9. API速查表

### 9.1 基础数据层

| 类名 | 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|------|
| BasicBars | get_daily(code, n) | code: 股票代码, n: 数量 | DataFrame | 日线数据 |
| BasicBars | get_weekly(code, n) | code: 股票代码, n: 数量 | DataFrame | 周线数据 |
| BasicBars | get_monthly(code, n) | code: 股票代码, n: 数量 | DataFrame | 月线数据 |
| BasicMinutes | get_data(code, date) | code: 股票代码, date: YYYYMMDD | DataFrame | 分时数据（普通） |
| BasicMinutesWithVR | get_data(code, date, n) | code: 股票代码, date: YYYYMMDD, n: 过去n日 | DataFrame | 分时数据（带量比）✨ |

### 9.2 指标数据层

| 类名 | 方法 | 参数 | 返回字段 | 说明 |
|------|------|------|----------|------|
| KDJIndicator | calculate(df) | df: 基础DataFrame | kdj_k, kdj_d, kdj_j | KDJ指标 |
| KDJIndicator | calculate(df) | n, m1, m2: 周期参数（初始化） | - | 自定义周期 |
| MACDIndicator | calculate(df) | df: 基础DataFrame | macd_dif, macd_dea, macd_macd | MACD指标 |
| MACDIndicator | calculate(df) | fast, slow, signal: 周期参数（初始化） | - | 自定义周期 |
| MAIndicator | calculate(df) | df: 基础DataFrame | ma5, ma10, ma20, ma60 | 均线指标（默认） |
| MAIndicator | calculate(df, periods) | periods: 周期列表（运行时） | maX | 动态周期 |
| MAIndicator | calculate(df) | periods: 周期列表（初始化） | maX | 自定义周期 |

**注意**：量比不再作为单纯指标，而是作为BasicMinutesWithVR基础数据类的一部分。

### 9.3 数据源层

| 类名 | 方法 | 说明 |
|------|------|------|
| ClientManager | get_client_count() | 查询缓存client数量 |
| ClientManager | get_cached_markets() | 查询缓存market列表 |
| ClientManager | has_client(market) | 检查market是否已缓存 |
| ClientManager | clear_cache() | 清空缓存（测试用） |

---

## 10. 最佳实践总结

### 10.1 推荐用法

1. **使用BasicBars/BasicMinutes获取数据**（而非直接调用TdxSource）
2. **批量处理时复用client**（ClientManager自动优化）
3. **一次计算多个指标**（避免重复获取基础数据）
4. **动态参数使用MAIndicator**（灵活切换不同周期）
5. **检查数据有效性**（避免空DataFrame导致错误）

### 10.2 性能建议

1. ClientManager自动管理client缓存，无需手动优化
2. 懒加载机制：首次使用时才初始化client
3. 多实例共享client：节省资源，提高效率
4. 批量处理：创建多个BasicBars实例自动共享client

### 10.3 错误处理建议

1. 检查DataFrame是否为空
2. 验证必需字段是否存在
3. 使用try-except捕获参数错误
4. 添加数据有效性检查逻辑

---

## 11. 示例代码汇总

完整示例代码位于：
- [examples/quick_test.py](../examples/quick_test.py) - 快速功能演示
- [examples/ma_dynamic_params_demo.py](../examples/ma_dynamic_params_demo.py) - MA动态参数演示
- [examples/client_manager_demo.py](../examples/client_manager_demo.py) - ClientManager性能演示
- [examples/basic_minutes_with_vr_demo.py](../examples/basic_minutes_with_vr_demo.py) - 分时量比完整演示 ✨新增

测试代码位于：
- [tests/test_basic_bars.py](../pystock_data/tests/test_basic_bars.py) - BasicBars测试
- [tests/test_basic_minutes.py](../pystock_data/tests/test_basic_minutes.py) - BasicMinutes测试
- [tests/test_basic_minutes_with_vr.py](../pystock_data/tests/test_basic_minutes_with_vr.py) - BasicMinutesWithVR测试 ✨新增
- [tests/test_kdj_indicator.py](../pystock_data/tests/test_kdj_indicator.py) - KDJIndicator测试
- [tests/test_macd_indicator.py](../pystock_data/tests/test_macd_indicator.py) - MACDIndicator测试
- [tests/test_ma_indicator.py](../pystock_data/tests/test_ma_indicator.py) - MAIndicator测试
- [tests/test_client_manager.py](../pystock_data/tests/test_client_manager.py) - ClientManager测试

---

本文档提供完整的API调用示例，帮助快速理解和使用PyStock数据层。更多详细信息请参考：
- [架构设计文档](architecture.md)
- [命名规范指南](naming_guide.md)
- [代码风格指南](code_style.md)
- [项目规范文档](../PROJECT_STANDARDS.md)