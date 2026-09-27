"""
本地数据落地配置（SQLite）

参数说明：
    DB_PATH              : 数据库文件路径（data/ 目录不入 git）
    DEFAULT_BACKFILL_DAYS: 首次同步回补深度（交易日数）
    BATCH_SIZE           : 批量同步大小，每同步 BATCH_SIZE 只后间隔一次
    BATCH_INTERVAL       : 批次之间的间隔（秒），防止请求过快触发限流
    FALLBACK_TTL         : get_daily 透传回源的最小间隔（秒），
                           避免停牌/非交易日股票每次读取都回源网络
"""

import os

# 数据库文件路径（本地数据，不入 git）
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'stocks.db')

# 首次同步回补深度（交易日数）
DEFAULT_BACKFILL_DAYS = 300

# 批量同步间隔（与 stock_monitor 约定一致）
BATCH_SIZE = 5
BATCH_INTERVAL = 0.2

# 透传回源限频（秒）
FALLBACK_TTL = 1800
