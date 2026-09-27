-- 日线落地表（阶段1）
-- 列对齐数据层标准输出；dt 存 bar 时间戳 ISO 文本，保证回读无损
CREATE TABLE IF NOT EXISTS daily_bars (
    code       TEXT NOT NULL,          -- 6位股票代码
    trade_date TEXT NOT NULL,          -- 交易日期 YYYY-MM-DD
    dt         TEXT NOT NULL,          -- bar 时间戳（ISO 格式）
    open  REAL,
    high  REAL,
    low   REAL,
    close REAL,
    volume REAL,
    amount REAL,
    PRIMARY KEY (code, trade_date)
);

-- 按日期维度的常用查询（水位/统计）
CREATE INDEX IF NOT EXISTS idx_daily_bars_date ON daily_bars (trade_date);
