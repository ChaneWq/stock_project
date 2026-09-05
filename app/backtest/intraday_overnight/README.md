intraday_overnight 日内超短回测 运行说明

一、基本用法
================================
命令模板（在项目根目录 D:\wu\space\trae\stock_project\stock_project 下运行）：

python -m app.backtest.intraday_overnight.main --code <代码> --flag-date <买入日> --sell <策略>

主题：flag_date 当日收盘价买入，下一交易日卖出
（下一交易日自动跳过周末/节假日）

通用参数：
  --code        股票代码（6位，必填）
  --flag-date   买入日期 YYYY-MM-DD（必填，当日收盘价买入）
  --sell        卖出策略，逗号分隔可多选对比（默认 close）
  --offset      日线拉取条数，默认300（flag_date 较久远时调大）
  --fallback    兜底时刻，默认 14:57（conditional/vr 用）
  --time        固定时刻，默认 10:00（fixed_time 用）
  --take-profit 止盈涨幅%，如 3 表示 +3%（conditional 用）
  --stop-loss   止损跌幅%，如 -2 表示 -2%（conditional 用）
  --vr          量比阈值，默认 2.5（vr 用）

二、各策略运行命令（可直接复制）
================================

1. open — 次日开盘卖
--------------------------------
逻辑：卖出日开盘价成交（隔夜情绪兑现）；无专属参数

python -m app.backtest.intraday_overnight.main --code 000059 --flag-date 2026-09-01 --sell open

2. close — 次日收盘卖（默认）
--------------------------------
逻辑：卖出日收盘价成交（持有整个次日交易日）；无专属参数

python -m app.backtest.intraday_overnight.main --code 000059 --flag-date 2026-09-01 --sell close

3. fixed_time — 次日固定时刻卖
--------------------------------
逻辑：指定时刻的分钟价格成交；时刻晚于 14:59 按收盘前最后一分钟
数据：分时
参数：
  --time  卖出时刻 HH:MM，默认 10:00，须在 09:30~14:59 内

python -m app.backtest.intraday_overnight.main --code 000059 --flag-date 2026-09-01 --sell fixed_time --time 10:00

4. conditional — 止盈/止损/兜底组合
--------------------------------
逻辑：盘中逐分钟扫描，先触发先卖；全天未触发 → fallback 时刻兜底
     两个条件都不传 = 纯兜底时刻卖
数据：分时
参数：
  --take-profit  止盈涨幅%，如 3；不传=不启用
  --stop-loss    止损跌幅%，如 -2；不传=不启用
  --fallback     兜底时刻，默认 14:57

python -m app.backtest.intraday_overnight.main --code 000059 --flag-date 2026-09-01 --sell conditional --take-profit 3 --stop-loss -2 --fallback 14:57

5. vr — 量比触发卖
--------------------------------
逻辑：盘中量比首次达到阈值即卖（放量兑现）；全天未达 → fallback 时刻兜底
数据：分时 + 量比（相对过去5日分钟均量）
参数：
  --vr       量比阈值，默认 2.5
  --fallback 兜底时刻，默认 14:57

python -m app.backtest.intraday_overnight.main --code 000059 --flag-date 2026-09-01 --sell vr --vr 2.5 --fallback 14:57

三、多策略对比（可直接复制）
================================
一次买入，多策略各自卖出，输出对比表：
  卖出价 / 卖出时刻 / 收益% / 盘中最大浮盈% / 最大浮亏% / 触发原因

python -m app.backtest.intraday_overnight.main --code 000059 --flag-date 2026-09-01 --sell open,close,fixed_time,conditional,vr --take-profit 3 --stop-loss -2 --time 10:00 --vr 2.5

四、常见报错
================================
- "不是交易日"            → flag_date 为非交易日，换交易日
- "是最新交易日"           → 下一交易日尚未到来，无法回测
- "超出最近300根K线范围"   → flag_date 太久远，调大 --offset（如 --offset 600）
