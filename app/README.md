# app 应用层说明文档

基于 `pystock_data` 数据层构建的应用集合，覆盖 监控 / 查询 / 扫描 / 选股 / 回测 / 指标研发 / 数据入库 全链路。

```
数据层取数 → 监控/查询展示 → 策略扫描/选股 → 回测验证 → 特征入库
```

---

## 1. stock_monitor — 自选股实时监控

- Flask Web 服务（`server.py`），自选股配置在 `stocks.csv`（列：code,name,remark,category，UTF-8 BOM）
- 数据刷新：5 秒自动刷新 + 手动刷新
- 表格功能：列拖拽排序、点击表头排序、分类 Tab 切换、可开关的均值汇总行
- 展示字段：最新价、分时量比曲线（紫色）、9:30/9:31 量比与涨幅、MA7 偏离度等
- 采集机制：ThreadPoolExecutor 多线程并发（线程独立客户端防连接冲突），批次间隔防 API 封禁
- 一键启动：`stock_monitor.bat`

## 2. stock_query — 个股数据查询

- Flask Web 服务（端口 5002），输入 6 位股票代码查询
- 日线查询：日期区间（start~end）或最近 N 个交易日，默认 30 日，按日期倒序
- 分时查询：指定单日，返回全天 240 条（9:30~14:59）
- 派生字段：涨幅%、成交量变化%、MA7、偏离度%、9:30/9:31 量比与涨幅
- 一键启动：`stock_query.bat`

## 3. minute_vr_scanner — 量比策略扫描器

- CLI + Web 双入口，对代码清单（`codes.txt`）批量扫描
- 内置策略：
  - `vr_slope`：量比斜率爬升（窗口斜率角度 + 量比/价格同步上涨）
  - `vr_anomaly`：量比异动（显性陡增 + 隐性转折检测）
- 支持参数：`--until` 模拟盘中任意时点运行、涨幅区间过滤、创业板/科创板/北交所板块过滤、CSV 导出、命中代码导出
- 一键启动：`minute_vr_scanner.bat`

## 4. backtest — 数据回测

每种策略独立目录。当前策略：`intraday_overnight`（日内超短：当日收盘买入，次日卖出）。

- 7 种卖出策略：`open`（次日开盘）/ `close`（次日收盘）/ `fixed_time`（固定时刻）/ `conditional`（止盈止损+兜底）/ `vr`（量比触发）/ `custom1`（止盈兜底收盘价）/ `custom2`（止盈兜底指定时刻）
- 多策略对比：一次买入，输出各策略 卖出价/时刻/收益%/最大浮盈浮亏%/触发原因
- 批量回测：CSV 输入（trade_date,code），多线程并行，同 code 日线只拉一次，输出明细 CSV + 按策略汇总（样本数/胜率/平均收益/最佳最差）
- 运行：`python -m app.backtest.intraday_overnight.main --code <代码> --flag-date <日期> --sell <策略>`

## 5. stock_selection — 选股器

筛选器/选股器模块，每种选股逻辑独立目录。

- `ma7_streak`：筛选"连续 N 日站上 MA7 且以小阴小阳爬升"的控盘蓄势形态个股
  - 输出：MA7 线上连续天数（streak）+ 小阴小阳质量指标 + 入选信号

## 6. index_develop — 自研指标研发

自研指标模块，目标：捕捉股票启动前的信号。每个指标独立目录。

- `vp_score`：量价打分指标
  - 量化"爆量后缩量回调蓄势"形态（爆量信号 → 缩量回调 → 启动确认/形态失败）
  - 输出：逐日评分表 + 关键事件，启动前给出高分预警

## 7. database — 数据库交互

涉及数据库的功能开发（数据入库等）。当前模块：`feature_import`。

- 从本地数据层提取分钟级/日线特征，批量写入 MySQL
- 配置：复制 `config.ini.example` 为 `config.ini`（不入 git）
- 支持按板块（`--board main`）、日期区间（`--start/--end`）批量导入
- 一键启动：`feature_import.bat`（交互式输入参数）

## 8. data_store — 本地数据落地（SQLite）

日线数据落地本地 SQLite（`data/stocks.db`，不入 git），供查询/回测/扫描读本地，批量场景不再反复走网络。

- **增量同步**：按每只股票的本地水位（MAX(trade_date)）只拉缺失部分；首次回补 300 个交易日
- **透传+回写读取**：`get_daily(code, start, end)` 本地覆盖直接返回（毫秒级），缺数据自动走网络补齐并回写；`start` 较早时自动深回补
- **输出一致**：列名/排序（最新在前）/trade_date 格式与数据层 `BasicBars.get_daily` 完全一致，调用方可无缝替换
- **幂等写入**：INSERT OR REPLACE，主键 (code, trade_date)，重复执行安全
- **并发安全**：WAL 模式（单写多读），写操作进程内串行锁；同步批次间隔防封禁
- CLI：
  ```
  python -m app.data_store.main --file app/minute_vr_scanner/codes.txt   # 增量同步清单
  python -m app.data_store.main --codes 000001,600519 --days 500         # 指定股票/回补深度
  python -m app.data_store.main --stats                                 # 查看本地库存概况
  ```
- Python 接口：`from app.data_store import get_daily, load_daily, sync_daily`

## 9. kline_view — 日K线可视化

每种实现独立子目录。当前：`demo_day_k`（demo 版）、`signal_day_k`（信号日回看）。

### demo_day_k — 日K线可视化（demo）

- Flask Web 服务（端口 5003），输入 6 位代码查看日K蜡烛图
- 主图：蜡烛图（红涨绿跌）+ MA5/10/20/60 均线；副图：成交量（按当日涨跌着色）
- 交互：区域缩放拖动、底部滑块选区间、十字光标联动左上角固定数据面板（日期/涨跌幅/OHLC/成交量/均线值，悬浮框已移除）
- 数据走 `data_store.get_daily`（本地 SQLite 优先，缺失按请求深度自动回源回写）
- 一键启动（demo 版）：`demo_day_k/demo.bat`，或 `python -m app.kline_view.demo_day_k.web`

### signal_day_k — 信号日K线回看

- Flask Web 服务（端口 5004），信号清单在 `signals.csv`（列：code,trade_date，UTF-8 BOM，本地维护不入 git）
- 展示信号日前 200 个交易日 ~ 后 20 个交易日的日K（共 221 根），MA5/10/20/60
- 信号日醒目标注：蜡烛金边 + 金色竖线（主图/成交量副图贯穿）+ 最高价上方「信号」标签；同股其它信号日以灰色点线弱标注
- 信号下拉选择 / 上一个下一个切换，打开图表信号日即居中可见；固定数据面板十字光标联动，信号日带高亮标记
- 边界处理：信号日为非交易日自动标注至前一交易日；信号日过近后侧不足 20 日显示到最新；页面均给出提示
- 一键启动：`signal_day_k/run.bat`，或 `python -m app.kline_view.signal_day_k.web`

---

## 模块约定

- 每个子模块独立目录，可带 `说明.txt`（一句话定位）和 `README.md`（详细说明）
- Web 类模块统一 Flask，模板放 `templates/` 子目录，一键启动用 `.bat`
- CLI 类模块通过 `python -m app.<模块>.main` 运行
- 策略类模块（回测/扫描/选股）每种策略独立文件，放在 `strategies/` 子目录
