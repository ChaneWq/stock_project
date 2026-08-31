"""
股票特征数据入库子项目

功能：
- 指定日期区间，全市场股票拉取日线并计算技术指标特征（tdx 公式库）
- 提取 09:30/09:31/09:32 分钟量比与价格特征
- 批量写入 DorisDB 表 stock_features4（仅插入，不建表）

模块：
- config: 配置读取（数据库连接/表名/日期窗口/并发参数）
- db_writer: DorisDB 数据写入（仅 INSERT）
- feature_extractor: 日线指标特征计算（公式来源 pystock_data.indicators.tdx）
- minute_feature: 分钟量比特征提取（基于 BasicMinutesWithVR）
- main: 入口，多线程编排

用法：
    python -m app.database.feature_import.main --dry-run --limit 5
    python -m app.database.feature_import.main --start 2026-08-25 --end 2026-08-29
"""
