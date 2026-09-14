# PyStock 项目概括

> 更新日期：2026-09-14

## 1. 项目简介

A股量化研究工具集。通过自研 `_tdxapi` 协议库直连通达信行情服务器获取数据，经过统一标准化后支撑技术指标计算与上层量化应用（选股、回测、监控、扫描、特征入库）。

核心设计原则：

- **严格分层**：数据源层 → 基础数据层 → 指标层 → 应用层，逐层增强 DataFrame
- **统一契约**：所有数据返回标准 DataFrame（`stock_code, datetime, open, close, high, low, volume, amount`）
- **文件驱动配置**：config.ini / csv / txt，无硬编码参数
- **模块自包含**：每个应用带 `.bat` 启动脚本 + `说明.txt`

## 2. 顶层目录职能

| 目录 | 职能 |
|------|------|
| `pystock_data/` | **数据层**。数据源封装、基础数据（K线/分时）、技术指标计算 |
| `app/` | **应用层**。基于数据层构建的量化应用，每个子目录一个独立应用 |
| `spider/` | **爬虫模块**。交易日历、上证指数等补充数据采集（requests 实现） |
| `small_tools/` | **小工具**。与主项目无必然关联的日常效率工具（如 copy_to_csv） |
| `docs/` | 项目文档（架构、API 使用指南、命名规范、代码风格） |
| `examples/` | 数据层使用示例（quick_test.py） |
| `PROJECT_STANDARDS.md` | 项目规范总文档 |

## 3. 数据层 pystock_data/

```
pystock_data/
├── source/               数据源层
│   ├── _tdxapi/            自研通达信协议库
│   │   ├── protocol/       协议编解码（组包/解包）
│   │   ├── network/        网络客户端（连接/心跳/自动重连）
│   │   ├── parser/         行情数据解析
│   │   ├── models/         数据模型（Bar / Quote / Tick）
│   │   └── utils/          工具函数
│   ├── tdx_source.py       数据源（fetch_bars / fetch_minutes / fetch_prev_n_day_vol）
│   ├── client_manager.py   客户端管理（共享单例 + 线程独立，懒连接）
│   └── utils.py            工具函数（字段标准化 standardize_fields 等）
│
├── basic/                基础数据层
│   ├── bars.py             BasicBars：日 / 周 / 月 K 线
│   ├── minutes.py          BasicMinutes：分时数据
│   └── minutes_with_vr.py  BasicMinutesWithVR：带量比的分时数据
│
├── indicators/           指标层（在基础 DataFrame 上追加指标列）
│   ├── kdj.py / macd.py / ma.py / vwap.py / vma.py / bbi.py
│   ├── zx.py / zxt.py / needle.py   重心类、针形形态指标
│   └── tdx/                通达信函数复刻（tdx_funcs / tdx_indicator）
│
├── demo/                 指标演示代码
└── tests/                测试（指标测试 + 回归测试）
```

数据流：`通达信服务器 → _tdxapi → TdxSource（标准化）→ Basic*（基础 DataFrame）→ Indicator*（增强 DataFrame）→ 应用`

## 4. 应用层 app/

| 应用 | 职能 | 入口 |
|------|------|------|
| `backtest/intraday_overnight` | 日内超短回测：flag_date 收盘买入、次日卖出，7 种可插拔卖出策略，支持 `--csv` 批量回测 | `python -m app.backtest.intraday_overnight.main` |
| `minute_vr_scanner` | 分钟量比扫描（Web），vr_slope / vr_anomaly 策略 | `minute_vr_scanner.bat` |
| `stock_monitor` | 股票监控（Web），监控列表由 stocks.csv 配置 | `stock_monitor.bat` |
| `stock_query` | 本地通达信数据查询（Web），日线/分时查询页面 | `stock_query.bat` |
| `database/feature_import` | 全市场日线指标特征 + 分钟量比特征入库 DorisDB，支持 `--dry-run` | `feature_import.bat` |
| `index_develop/vp_score` | 量价打分指标研发（单日量价分 + 形态累计分 + 状态机信号） | `vp_score.py` |
| `stock_selection/ma7_streak` | MA7 连续形态选股 | `ma7_streak.py` |

## 5. 爬虫层 spider/

| 模块 | 职能 |
|------|------|
| `base/base_spider.py` | 爬虫基类（requests 封装） |
| `calendar/` | 交易日历采集 |
| `sh_index/` | 上证指数采集 |
| `tests/` | 爬虫测试 |

## 6. 关键约定

- **数据源三方法契约**：`fetch_bars(code, freq, offset)` / `fetch_minutes(code, date)` / `fetch_prev_n_day_vol(code, n, date)`
- **K线频率编码**：`freq=9` 日线 / `5` 周线 / `6` 月线（通达信标准 category）
- **排序约定**：K 线倒序（最新在前），分时正序（从早到晚）
- **市场推断**：6 开头→SH，0/3 开头→SZ，4/8/9 开头→BJ（`normalize_code_market`）
- **外部依赖隔离**：行情协议实现只在 source 层，更换数据源不影响上层

## 7. 快速开始

```bash
# 安装依赖
pip install pandas numpy

# 运行测试
pytest pystock_data/tests/ -v

# 基础使用
from pystock_data import BasicBars, KDJIndicator
df = BasicBars().get_daily('000400', 100)
df = KDJIndicator().calculate(df)
```

详细文档见 [docs/](docs/)：API 使用指南（api_usage_guide.md）、架构设计（architecture.md）、数据层总览（pystock_data_overview.md）。
