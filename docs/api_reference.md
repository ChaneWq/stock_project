# API方法速查表

> 简洁快速查阅，详细用法见 [api_usage_guide.md](api_usage_guide.md)

---

## 1. 基础数据层

### BasicBars

K线数据

**初始化**：`BasicBars(market='std', thread_safe=False)`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| get_daily(code, n) | code: str, n: int | DataFrame | 日线 |
| get_weekly(code, n) | code: str, n: int | DataFrame | 周线 |
| get_monthly(code, n) | code: str, n: int | DataFrame | 月线 |
| get_latest(code) | code: str | DataFrame | 最新一根K线 |

**返回字段**：stock_code, datetime, trade_date, open, close, high, low, volume, amount

---

### BasicMinutes

分时数据（单日）

**初始化**：`BasicMinutes()`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| get_data(code, date) | code: str, date: str(YYYYMMDD) | DataFrame | 指定日期分时（240行） |
| get_data_by_range(code, start_date, end_date) | code: str, start_date: str, end_date: str | DataFrame | 日期范围内分时（未实现） |

**返回字段**：stock_code, datetime, trade_date, open, close, high, low, volume, amount, hour, minute

---

### BasicMinutesWithVR

带量比的分时数据（需过去n日数据）

**初始化**：`BasicMinutesWithVR(market='std', thread_safe=False, source=None)`（source 可注入共享的 TdxSource 实例）

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| get_data(code, date, n, prev_day_vol_list) | code: str, date: str, n: int=5, prev_day_vol_list: list=None | DataFrame | 带量比分时数据（prev_day_vol_list 可外部注入n日成交量） |
| get_avg_vol_per_minute() | 无 | float | 过去n日分钟均量 |
| get_prev_n_day_vol_list() | 无 | list | 过去n日成交量列表 |
| get_prev_close() | 无 | float | 昨收价 |
| get_volume_ratio_summary(vr_df) | vr_df: DataFrame | dict | 量比统计{max,min,avg,current} |
| get_volume_ratio_trend(vr_df, window) | vr_df: DataFrame, window: int=10 | str | 趋势(上升/下降/平稳) |
| filter_volume_ratio_by_range(vr_df, min_vr, max_vr) | vr_df: DataFrame, min_vr: float=None, max_vr: float=None | DataFrame | 按量比范围过滤 |
| find_volume_ratio_peaks(vr_df, threshold) | vr_df: DataFrame, threshold: float=3.0 | list | 量比峰值[(time, vr), ...] |

**返回字段**：BasicMinutes全部字段 + volume_ratio, cumulative_vol, time_index, avg_vol_per_minute

---

## 2. 指标数据层

### KDJIndicator

KDJ指标

**初始化**：`KDJIndicator(n=9, m1=3, m2=3)`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| calculate(df) | df: DataFrame | DataFrame | 计算KDJ |

**新增字段**：kdj_k, kdj_d, kdj_j（均保留两位小数）

---

### MACDIndicator

MACD指标

**初始化**：`MACDIndicator(fast_period=12, slow_period=26, signal_period=9)`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| calculate(df) | df: DataFrame | DataFrame | 计算MACD |

**新增字段**：macd_dif, macd_dea, macd_macd（均保留两位小数）

---

### MAIndicator

均线指标（支持动态参数）

**初始化**：`MAIndicator(periods=None)`（默认[5, 10, 20, 60]）

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| calculate(df, periods) | df: DataFrame, periods: List[int]=None | DataFrame | 计算MA（periods可运行时指定） |
| get_periods() | 无 | List[int] | 获取当前周期列表 |

**新增字段**：ma5, ma10, ma20, ma60（或自定义ma{N}，均保留两位小数）

**要求字段**：close

---

### VWAPIndicator

分时累计均价（VWAP口径）

**初始化**：`VWAPIndicator()`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| calculate(df) | df: DataFrame | DataFrame | 计算累计均价 |

**新增字段**：avg_price（累计成交额/累计成交量，保留三位小数）

**要求字段**：volume；价格字段自适应（close 或 price）；amount 缺失时按 价格×成交量 估算

---

### VolumeMAIndicator

成交量均线（判断放量/缩量）

**初始化**：`VolumeMAIndicator(periods=None)`（默认[5]）

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| calculate(df, periods) | df: DataFrame, periods: List[int]=None | DataFrame | 计算VMA（periods可运行时指定） |

**新增字段**：vma5（或自定义vma{N}，均保留两位小数）

**要求字段**：volume

---

### BBIIndicator

多空指数（BBI）

**初始化**：`BBIIndicator(m1=3, m2=6, m3=12, m4=24)`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| calculate(df) | df: DataFrame | DataFrame | 计算BBI |

**新增字段**：bbi（保留两位小数）

**要求字段**：close

---

### ZXTIndicator

重心通道指标

**初始化**：`ZXTIndicator(n=4, m1=4, m2=6)`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| calculate(df) | df: DataFrame | DataFrame | 计算ZXT |

**新增字段**：zxt（保留两位小数）

**要求字段**：high, low, close

---

### ZXShortTermTrendIndicator

短期趋势线指标

**初始化**：`ZXShortTermTrendIndicator(n=10)`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| calculate(df) | df: DataFrame | DataFrame | 计算短期趋势线 |

**新增字段**：zx_short_term_trend（保留两位小数）

**要求字段**：close

---

### ZXBullBearLineIndicator

牛熊分界线指标

**初始化**：`ZXBullBearLineIndicator(m1=14, m2=28, m3=57, m4=114)`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| calculate(df) | df: DataFrame | DataFrame | 计算牛熊分界线 |

**新增字段**：zx_bull_bear_line（保留两位小数）

**要求字段**：close

---

### DZTIndicator / DZSIndicator

针形形态指标（顶部针 / 底部针）

**初始化**：`DZTIndicator()` / `DZSIndicator()`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| calculate(df) | df: DataFrame | DataFrame | 识别针形形态 |

**新增字段**：dzt（顶部针） / dzs（底部针）

**要求字段**：high, low, close

---

### tdx 函数库（indicators/tdx/）

通达信公式函数库，项目唯一的指标公式来源，供自研指标开发使用：

- **tdx_funcs 序列原语（39 个）**：
  - 引用类：REF, DIFF, RET, CONST, VALUEWHEN
  - 统计类：MA, EMA, SMA, DMA, WMA, STD, SUM, AVEDEV, SLOPE, FORCAST, HHV, LLV, HHVBARS, LLVBARS
  - 逻辑类：IF, AND, OR, CROSS, CROSS_UP, CROSS_DOWN, LONGCROSS, LAST, COUNT, EVERY, EXIST, FILTER, BARSLAST, BARSLASTCOUNT, BARSSINCEN
  - 工具类：RD, ABS, MAX, MIN, RANGE
- **tdx_indicator 指标函数（100+ 个）**：MACD, KDJ, RSI, BOLL, ATR, DMI, WR, OBV, SAR, CCI, SKDJ, TRIX, EMV, PSY, VR 等

```python
from pystock_data.indicators.tdx import MACD, KDJ, MA, EMA, CROSS

# 输入 numpy 数组，返回元组
dif, dea, macd = MACD(df['close'].values)
k, d, j = KDJ(df['close'].values, df['high'].values, df['low'].values)
```

---

## 3. 数据源层

### ClientManager

客户端缓存管理（类方法，无需实例化）

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| get_client() | 无 | TdxClient | 获取/创建共享client（懒连接，内置心跳+自动重连） |
| get_thread_client() | 无 | TdxClient | 获取线程独立client（多线程高并发用） |
| has_client(market) | market: str='std' | bool | 是否已缓存（兼容旧接口） |
| get_client_count() | 无 | int | 缓存数量 |
| get_cached_markets() | 无 | list | 已缓存市场列表（兼容旧接口） |
| clear_cache() | 无 | None | 清空缓存 |

---

### TdxSource

通达信数据源（基于自研 _tdxapi 协议库）

**初始化**：`TdxSource(market='std', thread_safe=False)`（thread_safe=True 时使用线程独立client）

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| fetch_bars(code, freq, offset) | code: str, freq: int, offset: int | DataFrame | K线数据（单次800条，超出自动分页） |
| fetch_minutes(code, date) | code: str, date: str | DataFrame | 分时数据 |
| fetch_prev_n_day_vol(code, n, date) | code: str, n: int=5, date: str=None | dict | 过去n日成交量{vol_list, prev_close}（指定date时结果缓存） |
| fetch_realtime(codes) | codes: list | DataFrame | 实时数据（未实现） |

**freq参数**：9=日线, 5=周线, 6=月线

**市场推断**：按股票代码自动判断（6开头→SH，0/3开头→SZ，4/8/9开头→BJ），无需手动指定

---

## 4. 爬虫层

### ShIndexSpider

上证指数爬虫（搜狐财经）

**初始化**：`ShIndexSpider()`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| get_daily(code, start_date, end_date) | code: str='zs_000001', start_date: str, end_date: str | DataFrame | 日线 |
| get_weekly(code, start_date, end_date) | code: str='zs_000001', start_date: str, end_date: str | DataFrame | 周线 |
| get_monthly(code, start_date, end_date) | code: str='zs_000001', start_date: str, end_date: str | DataFrame | 月线 |

**返回字段**：date, open, close, high, low, volume, amount, change_pct

**指数代码**：zs_000001(上证), zs_399001(深证), zs_399006(创业板)

---

### CalendarSpider

日历数据爬虫（bmcx万年历）

**初始化**：`CalendarSpider()`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| get_calendar(start_date, end_date, delay) | start_date: str, end_date: str, delay: float=0.5 | DataFrame | 日历数据 |
| get_trade_calendar(start_date, end_date, delay) | start_date: str, end_date: str, delay: float=0.5 | DataFrame | 交易日历（过滤周末） |

**返回字段**：date, year, month, day, weekday, lunar_month, lunar_day, lunar_date, ganzhi_year, zodiac_year, ganzhi_month, ganzhi_day, festival

**日期格式**：YYYY-MM-DD

---

## 5. 导入方式

```python
# 基础数据层
from pystock_data import BasicBars, BasicMinutes, BasicMinutesWithVR

# 指标数据层
from pystock_data.indicators import KDJIndicator, MACDIndicator, MAIndicator

# 数据源层
from pystock_data.source import ClientManager, TdxSource

# 爬虫层
from spider import ShIndexSpider, CalendarSpider
```

---

## 6. 快速示例

```python
# K线 + 指标
df = BasicBars().get_daily('000400', 100)
df = KDJIndicator().calculate(df)
df = MAIndicator().calculate(df, periods=[5, 10, 20])

# 分时 + 量比
vr_df = BasicMinutesWithVR().get_data('000400', '20260624', n=5)

# 上证指数
sh_df = ShIndexSpider().get_daily('zs_000001', '20260101', '20260624')

# 日历数据
cal_df = CalendarSpider().get_calendar('2026-01-01', '2026-06-24')
```
