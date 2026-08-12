# Spider API速查表

> 爬虫子项目，简洁快速查阅

---

## 1. BaseSpider

爬虫基类（通常不直接使用，供子类继承）

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| fetch_html(url, headers, timeout) | url: str, headers: Dict=None, timeout: int=10 | str/None | 获取HTML内容 |
| fetch_text(url, params, headers, timeout) | url: str, params: Dict=None, headers: Dict=None, timeout: int=10 | str/None | 获取响应文本（JSONP等） |

---

## 2. ShIndexSpider

上证指数爬虫（搜狐财经）

**继承**：BaseSpider

**初始化**：`ShIndexSpider()`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| get_daily(code, start_date, end_date) | code: str='zs_000001', start_date: str, end_date: str | DataFrame | 日线 |
| get_weekly(code, start_date, end_date) | code: str='zs_000001', start_date: str, end_date: str | DataFrame | 周线 |
| get_monthly(code, start_date, end_date) | code: str='zs_000001', start_date: str, end_date: str | DataFrame | 月线 |

**返回字段**：date, open, close, high, low, volume, amount, change_pct

**指数代码**：zs_000001(上证), zs_399001(深证), zs_399006(创业板)

**日期格式**：YYYYMMDD（如 '20260101'）

**数据来源**：https://q.stock.sohu.com/hisHq

---

## 3. CalendarSpider

日历数据爬虫（bmcx万年历）

**继承**：BaseSpider

**初始化**：`CalendarSpider()`

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| get_calendar(start_date, end_date, delay) | start_date: str, end_date: str, delay: float=0.5 | DataFrame | 日历数据 |
| get_trade_calendar(start_date, end_date, delay) | start_date: str, end_date: str, delay: float=0.5 | DataFrame | 交易日历（过滤周末） |

**返回字段**：date, year, month, day, weekday, lunar_month, lunar_day, lunar_date, ganzhi_year, zodiac_year, ganzhi_month, ganzhi_day, festival

**日期格式**：YYYY-MM-DD（如 '2026-06-24'）

**数据来源**：https://wannianrili.bmcx.com

**优化**：每月只请求一次HTML（同月数据在同一页面）

---

## 4. 导入方式

```python
# 导入全部
from spider import ShIndexSpider, CalendarSpider, BaseSpider

# 单独导入
from spider.sh_index import ShIndexSpider
from spider.calendar import CalendarSpider
```

---

## 5. 快速示例

```python
from spider import ShIndexSpider, CalendarSpider

# 上证指数日线
sh_df = ShIndexSpider().get_daily('zs_000001', '20260101', '20260624')

# 日历数据
cal_df = CalendarSpider().get_calendar('2026-06-01', '2026-06-30')

# 交易日历
trade_df = CalendarSpider().get_trade_calendar('2026-06-01', '2026-06-30')
```

---

## 6. 目录结构

```
spider/
├── __init__.py              # 导出 ShIndexSpider, CalendarSpider, BaseSpider
├── docs/
│   └── api_reference.md     # 本文档
├── base/
│   ├── __init__.py
│   └── base_spider.py       # BaseSpider 基类
├── sh_index/
│   ├── __init__.py
│   ├── sh_index_spider.py   # ShIndexSpider 上证指数爬虫
│   └── example_sh_index.py  # 调用示例
├── calendar/
│   ├── __init__.py
│   ├── calendar_spider.py   # CalendarSpider 日历爬虫
│   └── example_calendar.py  # 调用示例
└── tests/
    ├── __init__.py
    └── test_spider.py       # 测试文件
```
