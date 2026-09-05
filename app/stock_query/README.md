# 个股数据查询（stock_query）

本地数据源（通达信 TdxSource）的个股日线、分时数据查询页面，带 Web 界面。

## 启动

双击 `stock_query.bat`，或项目根目录执行：

```
python -m app.stock_query.web
```

访问：http://127.0.0.1:5002/

## 使用

输入 6 位股票代码（如 `000712`），支持三种查询方式：

- 日期区间：start ~ end（如 2026-08-01 ~ 2026-08-31）
- 最近 N 个交易日：填 recent（如 30）
- 分时数据：选单个日期，查询该交易日全天分时（9:30~14:59，240 条正序）

日线默认查询最近 30 个交易日，结果按日期倒序（最新在前）。

## 返回字段

日线：

| 字段 | 含义 |
|---|---|
| trade_date | 交易日 |
| today_rate | 涨幅%（相对昨收） |
| vol / vol_chg_pct | 成交量 / 成交量变化% |
| MA7 | 含当日的 7 日均线 |
| dev_pct | 收盘价与 MA7 偏离度% |
| vol_ratio_0930 / rate_0930 | 9:30 分时量比 / 涨幅 |
| vol_ratio_0931 / rate_0931 | 9:31 分时量比 / 涨幅 |

分时（单日 240 条）：

| 字段 | 含义 |
|---|---|
| time | 时间（HH:MM） |
| price | 该分钟价格 |
| rate_pct | 涨幅%（相对昨收） |
| volume | 该分钟成交量 |
| cumulative_vol | 当日累计成交量 |
| volume_ratio | 量比（基准：过去 5 日分钟均量） |

## 接口

- `GET /api/query?code=xxx&start=...&end=...` 或 `&recent=N` — 日线查询
- `GET /api/minutes?code=xxx&date=YYYY-MM-DD` — 分时查询

## 文件说明

- `web.py` — Flask 服务，页面 + `/api/query`、`/api/minutes` 接口
- `query.py` — 查询逻辑（日线 + 分时量比 + 派生字段计算）
- `templates/index.html` — 前端页面
- `stock_query.bat` — 一键启动脚本
