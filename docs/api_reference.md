# API方法速查表

> 简洁快速查阅，详细用法见 [api_usage_guide.md](api_usage_guide.md)

---

## 1. 基础数据层

### BasicBars

K线数据

**初始化**：`BasicBars(market='std')`

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

**初始化**：`BasicMinutes(market='std')`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| get_data(code, date) | code: str, date: str(YYYYMMDD) | DataFrame | 指定日期分时（240行） |

**返回字段**：stock_code, datetime, trade_date, open, close, high, low, volume, amount, hour, minute

---

### BasicMinutesWithVR

带量比的分时数据（需过去n日数据）

**初始化**：`BasicMinutesWithVR(market='std')`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| get_data(code, date, n) | code: str, date: str, n: int=5 | DataFrame | 带量比分时数据 |
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

## 3. 数据源层

### ClientManager

客户端缓存管理（类方法，无需实例化）

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| get_client(market) | market: str='std' | Quotes | 获取/创建client |
| has_client(market) | market: str='std' | bool | 是否已缓存 |
| get_client_count() | 无 | int | 缓存数量 |
| get_cached_markets() | 无 | list | 已缓存市场列表 |
| clear_cache() | 无 | None | 清空缓存 |

---

### TdxSource

通达信数据源

**初始化**：`TdxSource(market='std')`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| fetch_bars(code, freq, offset) | code: str, freq: int, offset: int | DataFrame | K线数据 |
| fetch_minutes(code, date) | code: str, date: str | DataFrame | 分时数据 |
| fetch_prev_n_day_vol(code, n, date) | code: str, n: int=5, date: str=None | dict | 过去n日成交量{vol_list, prev_close} |
| fetch_realtime(codes) | codes: list | DataFrame | 实时数据（未实现） |

**freq参数**：9=日线, 10=周线, 11=月线, 8=分钟线

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
