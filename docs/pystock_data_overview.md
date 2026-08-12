# pystock_data 代码说明文档

> 本文档对 `pystock_data/` 目录下的代码进行整体说明，涵盖目录结构、各模块职责、关键实现细节及数据流转过程。
> 方法签名速查请参考 [api_reference.md](api_reference.md)，架构设计理念请参考 [architecture.md](architecture.md)。

---

## 1. 模块概述

`pystock_data` 是 PyStock 项目的**数据层包**，负责从通达信（mootdx）数据源获取行情数据，并对外提供标准化的 K 线、分时数据以及技术指标计算能力。

### 设计分层

```
pystock_data/
├── source/      数据源层：封装 mootdx，统一管理客户端
├── basic/       基础数据层：标准化 K 线 / 分时 / 带量比分时
└── indicators/  指标数据层：在基础 DataFrame 上计算技术指标
```

数据自下而上流动：`source → basic → indicators`，每一层都基于下层输出并**增强** DataFrame（添加字段），最终对外暴露统一接口。

### 顶层导出

[`pystock_data/__init__.py`](../pystock_data/__init__.py) 导出核心类：

```python
from pystock_data import (
    BasicBars,          # 基础K线
    BasicMinutes,       # 基础分时
    BasicMinutesWithVR, # 带量比分时
    KDJIndicator,       # KDJ指标
    MACDIndicator,      # MACD指标
    MAIndicator,        # 均线指标
)
```

---

## 2. 目录结构

```
pystock_data/
├── __init__.py                  顶层包，导出核心类
├── source/                      数据源层
│   ├── __init__.py              导出 TdxSource / ClientManager / standardize_fields
│   ├── client_manager.py        客户端缓存管理器（单例缓存）
│   ├── tdx_source.py            通达信数据源（K线/分时/历史量）
│   └── utils.py                 字段标准化、分时时间字段、数据校验
├── basic/                       基础数据层
│   ├── __init__.py              导出 BasicBars / BasicMinutes / BasicMinutesWithVR
│   ├── bars.py                  K线数据（日/周/月线）
│   ├── minutes.py               普通分时数据（单日240分钟）
│   └── minutes_with_vr.py        带量比的分时数据（含完整量比分析）
└── indicators/                  指标数据层
    ├── __init__.py              导出 IndicatorBase / KDJ / MACD / MA
    ├── base.py                  指标基类（接口与输入校验）
    ├── kdj.py                   KDJ 指标
    ├── macd.py                  MACD 指标
    └── ma.py                    均线指标（支持动态周期）
```

> `tests/` 子目录为单元测试，不在本说明范围内。

---

## 3. 数据源层（source）

### 3.1 `client_manager.py` — ClientManager

**职责**：统一管理通达信 `Quotes` 客户端实例，避免重复初始化。

**设计要点**：
- 全部为 `@classmethod`，**无需实例化**即可调用。
- 内部以类变量 `_clients = {}` 作为缓存字典，键为 `market`，值为 `Quotes` 实例。
- **懒加载**：首次 `get_client(market)` 时才通过 `Quotes.factory(market=market)` 创建并缓存；后续直接返回缓存实例。
- 同一个 `market` 的多个 `TdxSource` 实例共享同一个 client。

**主要方法**：

| 方法 | 说明 |
|------|------|
| `get_client(market='std')` | 获取或创建客户端（缓存复用） |
| `has_client(market)` | 是否已缓存 |
| `get_client_count()` | 缓存数量 |
| `get_cached_markets()` | 已缓存市场列表 |
| `clear_cache()` | 清空缓存（主要用于测试） |

### 3.2 `tdx_source.py` — TdxSource

**职责**：封装 mootdx 调用，对外提供 K 线、分时、历史成交量数据获取接口。

**设计要点**：
- 构造时仅保存 `self.market`，**不持有 client**，运行时通过 `ClientManager.get_client(self.market)` 获取（懒加载 + 缓存复用）。
- 所有 `fetch_*` 方法采用 `try/except` 包裹，失败时打印日志并返回空 `DataFrame` / `None`，不抛出异常。
- K 线结果经过 [`standardize_fields`](../pystock_data/source/utils.py) 标准化；分时结果经过 [`add_minute_fields`](../pystock_data/source/utils.py) 处理。

**主要方法**：

| 方法 | 参数 | 返回 | 说明 |
|------|------|------|------|
| `fetch_bars(code, freq, offset)` | freq: 9=日 / 5=周 / 6=月 | DataFrame | 标准化 K 线 |
| `fetch_minutes(code, date)` | date: YYYYMMDD | DataFrame | 分时（含 hour/minute） |
| `fetch_prev_n_day_vol(code, n=5, date=None)` | date 为 None 取最新 | dict `{vol_list, prev_close}` | 过去 n 日成交量与昨收价 |
| `fetch_realtime(codes)` | — | — | **未实现**（NotImplementedError） |

> **频率映射说明**：代码中 `freq=9` 为日线、`freq=5` 为周线、`freq=6` 为月线（见 [bars.py](../pystock_data/basic/bars.py)）。

### 3.3 `utils.py` — 工具函数

**职责**：字段标准化、分时时间生成、数据校验。

- **`standardize_fields(df, stock_code=None)`**
  - 字段重命名：`vol → volume`；统一保留 `open/close/high/low/volume/amount`。
  - 处理 `datetime` 既是索引又是列的情况；生成 `trade_date`（YYYY-MM-DD）与 `stock_code`。
  - 按标准列顺序输出。
- **`add_minute_fields(df, stock_code=None, date=None)`**
  - 分时数据无 `datetime` 字段时，按 240 分钟生成时间序列：
    - 上午 9:30–11:30（120 分钟）
    - 下午 13:00–14:59（120 分钟）
  - 衍生 `hour` / `minute` 字段后调用 `standardize_fields`。
- **`validate_bar_data(df)` / `validate_minute_data(df)`**
  - 检查必需字段是否存在，返回 bool。

---

## 4. 基础数据层（basic）

### 4.1 `bars.py` — BasicBars

**职责**：提供日 / 周 / 月线数据，统一字段格式与排序。

**设计要点**：
- 构造时创建一个 `TdxSource()` 实例（其 client 由 ClientManager 复用）。
- 所有方法将结果按 `datetime` **倒序**排列（最新数据在第一行），并 `reset_index(drop=True)`。

**主要方法**：

| 方法 | 默认 n | freq | 说明 |
|------|--------|------|------|
| `get_daily(code, n=400)` | 400 | 9 | 日线 |
| `get_weekly(code, n=100)` | 100 | 5 | 周线 |
| `get_monthly(code, n=100)` | 100 | 6 | 月线 |
| `get_latest(code)` | 1 | 9 | 最新一根日线 |

**返回字段**：`stock_code, datetime, trade_date, open, close, high, low, volume, amount`

### 4.2 `minutes.py` — BasicMinutes

**职责**：获取单日分时数据（240 分钟）。

**设计要点**：
- 结果按 `datetime` **正序**排列（从早到晚）。
- `get_data_by_range` 为**未实现**（NotImplementedError），预留扩展。

**主要方法**：

| 方法 | 说明 |
|------|------|
| `get_data(code, date)` | 指定日期分时（240 行） |
| `get_data_by_range(code, start_date, end_date)` | 未实现 |

**返回字段**：BasicBars 全部字段 + `hour, minute`

### 4.3 `minutes_with_vr.py` — BasicMinutesWithVR

**职责**：在分时数据基础上自动计算量比，并提供完整的量比分析能力。

**设计要点**：
- 构造时接收 `market` 参数（默认 `'std'`），这是 basic 层中**唯一**支持 market 配置的类。
- `get_data` 内部三步：
  1. `fetch_minutes` 获取当日分时
  2. `fetch_prev_n_day_vol` 获取过去 n 日成交量与昨收价
  3. 计算量比并写入 DataFrame
- 缓存中间结果（`_avg_vol_per_minute` / `_prev_n_day_vol_list` / `_prev_close`），供后续查询方法使用。

**量比计算公式**：

```
每分钟均量(avg_vol_per_minute) = sum(过去n日成交量) / (n * 240)
时间序号(time_index)           = 通达信公式（1~240）
量比(volume_ratio)             = 累计成交量 / 时间序号 / 每分钟均量
```

时间序号公式（向量化实现）：

```
上午: (HOUR-9)*60 + MINUTE - 30
下午: (HOUR-13)*60 + MINUTE + 120
结果 + 1
```

验证：9:30→1，11:29→120，13:00→121，14:59→240。

**新增字段**：`volume_ratio, cumulative_vol, time_index, avg_vol_per_minute`

**量比分析方法**：

| 方法 | 说明 |
|------|------|
| `get_avg_vol_per_minute()` | 过去 n 日每分钟均量 |
| `get_prev_n_day_vol_list()` | 过去 n 日成交量列表 |
| `get_prev_close()` | 昨收价 |
| `get_volume_ratio_summary(vr_df)` | 统计摘要 `{max, min, avg, current}` |
| `get_volume_ratio_trend(vr_df, window=10)` | 趋势：上升/下降/平稳/数据不足 |
| `filter_volume_ratio_by_range(vr_df, min_vr=None, max_vr=None)` | 按量比范围过滤 |
| `find_volume_ratio_peaks(vr_df, threshold=3.0)` | 量比峰值列表（按量比降序） |

> 量比没有放在 `indicators/` 层，因为它依赖多日历史数据，更适合与分时数据一体化获取。

---

## 5. 指标数据层（indicators）

### 5.1 `base.py` — IndicatorBase

**职责**：定义指标计算的标准接口与输入校验。

**设计要点**：
- 构造要求 `name` 与 `required_fields`。
- `calculate(df)` 为抽象方法，子类必须实现，否则抛 `NotImplementedError`。
- `validate_input(df)` 检查空 DataFrame 与必需字段，缺失时打印日志并返回 `False`。
- 子类 `calculate` 开头通常先 `validate_input`，失败则返回 `df.copy()` 不抛异常。

### 5.2 `ma.py` — MAIndicator

**职责**：计算多条均线。

**设计要点**：
- **支持动态周期**：初始化时设置 `periods`，`calculate` 时可临时传入 `periods` 覆盖，不传则用初始化值。
- 字段命名：`ma{period}`（如 `ma5, ma10, ma20, ma60`）。
- 使用 `rolling(window, min_periods=1)`，结果保留两位小数。
- `_validate_periods` 校验：必须为非空列表且元素均为正整数。

**必需字段**：`close`

### 5.3 `macd.py` — MACDIndicator

**职责**：计算 MACD 三值。

**参数**：`fast_period=12, slow_period=26, signal_period=9`

**计算逻辑**：
```
ema_fast = close 的 fast_period 周期 EMA
ema_slow = close 的 slow_period 周期 EMA
macd_dif  = ema_fast - ema_slow
macd_dea  = dif 的 signal_period 周期 EMA
macd_macd = 2 * (dif - dea)
```

- 使用 `ewm(span=..., adjust=False)`。
- 结果保留两位小数。

**必需字段**：`close`

### 5.4 `kdj.py` — KDJIndicator

**职责**：计算 KDJ 三值。

**参数**：`n=9, m1=3, m2=3`

**计算逻辑**：
```
low_n  = low 的 n 周期最小值
high_n = high 的 n 周期最大值
rsv = (close - low_n) / (high_n - low_n) * 100
rsv = rsv.fillna(50)            # 处理除零
kdj_k = rsv 的 (m1-1) com EMA
kdj_d = kdj_k 的 (m2-1) com EMA
kdj_j = 3 * kdj_k - 2 * kdj_d
```

- 使用 `ewm(com=..., adjust=False)`。
- 结果保留两位小数。

**必需字段**：`high, low, close`

---

## 6. 数据流转

### 6.1 K 线 + 指标

```
应用调用
  └─ BasicBars.get_daily('000400', 400)
       └─ TdxSource.fetch_bars(code, 9, 400)
            └─ ClientManager.get_client('std')   [缓存复用]
            └─ mootdx client.bars(...)
            └─ standardize_fields(df, code)
       └─ 按 datetime 倒序
  → 标准基础 DataFrame
  └─ KDJIndicator().calculate(df)    → 增加 kdj_k/d/j
  └─ MACDIndicator().calculate(df)   → 增加 macd_dif/dea/macd
  └─ MAIndicator().calculate(df)     → 增加 ma{N}
  → 最终增强 DataFrame（基础字段 + 多指标字段）
```

### 6.2 带量比分时

```
BasicMinutesWithVR().get_data('000400', '20260624', n=5)
  ├─ TdxSource.fetch_minutes(code, date)              [add_minute_fields]
  ├─ TdxSource.fetch_prev_n_day_vol(code, 5, date)     [vol_list, prev_close]
  ├─ 计算 avg_vol_per_minute = sum(vol_list) / (5*240)
  └─ 计算 time_index / cumulative_vol / volume_ratio
  → 带量比的分时 DataFrame
  → 可继续调用 get_volume_ratio_summary / find_volume_ratio_peaks 等
```

---

## 7. 关键设计点

1. **ClientManager 缓存复用**：所有 `TdxSource` 共享同一 `market` 的 client，避免重复初始化 `Quotes.factory`，节省网络与资源开销。
2. **字段标准化**：`standardize_fields` 统一 `vol → volume`、补 `trade_date` / `stock_code`，保证基础层输出列名一致，便于指标层消费。
3. **DataFrame 增强机制**：指标层只新增列、不删除原有列，多个指标可链式叠加。
4. **输入校验**：指标基类 `validate_input` 检查 `required_fields`，校验失败返回 `df.copy()`，避免中断调用链。
5. **量比一体化**：量比依赖多日数据，故放在 `BasicMinutesWithVR` 而非指标层，对外一次调用即可拿到完整结果。

---

## 8. 使用示例

```python
from pystock_data import (
    BasicBars, BasicMinutes, BasicMinutesWithVR,
    KDJIndicator, MACDIndicator, MAIndicator,
)

# K线 + 多指标链式计算
df = BasicBars().get_daily('000400', 400)
df = KDJIndicator().calculate(df)
df = MACDIndicator().calculate(df)
df = MAIndicator().calculate(df, periods=[5, 10, 20, 60])

# 普通分时
minute_df = BasicMinutes().get_data('000400', '20260624')

# 带量比分时 + 分析
vr = BasicMinutesWithVR()
vr_df = vr.get_data('000400', '20260624', n=5)
summary = vr.get_volume_ratio_summary(vr_df)
peaks = vr.find_volume_ratio_peaks(vr_df, threshold=3.0)

# 直接使用数据源层（高级）
from pystock_data.source import ClientManager, TdxSource
ClientManager.get_client('std')           # 预热客户端
raw = TdxSource().fetch_bars('000400', 9, 100)
```

---

## 9. 注意事项

- **未实现的方法**：
  - `TdxSource.fetch_realtime(codes)`
  - `BasicMinutes.get_data_by_range(code, start_date, end_date)`
- **market 参数范围**：仅 `BasicMinutesWithVR` 与 `TdxSource` 接收 `market`；`BasicBars` / `BasicMinutes` 使用默认 `'std'`。
- **`fetch_prev_n_day_vol` 的 `vol_list`**：取自 mootdx 原始 `vol` 字段，未经标准化为 `volume`，单位与 `BasicBars` 的 `volume` 一致。
- **指标 EMA 实现**：MACD 用 `ewm(span=..., adjust=False)`，KDJ 用 `ewm(com=m-1, adjust=False)`，两者平滑参数语义不同。
- **数据排序约定**：K 线倒序（最新在前），分时正序（从早到晚），下游使用时注意方向。

---

**文档版本**：1.0.0  
**最后更新**：2026-08-12
