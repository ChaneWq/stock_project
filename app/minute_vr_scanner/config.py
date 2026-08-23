"""
性能优化配置

参数说明：
    BATCH_SIZE       : 批量采集大小，每采集 BATCH_SIZE 只后间隔一次
    BATCH_INTERVAL   : 批次之间的间隔（秒），防止请求过快触发限流
                       0 表示不间隔
    MAX_WORKERS      : 并发采集线程数
                       每个线程创建独立 client（基于 threading.local），互不影响
                       1 表示串行（等价于不并发）；推荐 3
                       增大可提速但会增加连接数，封禁风险略增

间隔示例：
    BATCH_SIZE=5, BATCH_INTERVAL=0.2 → 25只 = 4批 × 0.2s = 0.8s 间隔
    BATCH_SIZE=1, BATCH_INTERVAL=0.1 → 退化为每只间隔0.1s（最保守）
    BATCH_SIZE=999, BATCH_INTERVAL=0 → 不间隔（最快，封禁风险高）
"""

# 批量采集间隔：每 BATCH_SIZE 只后间隔 BATCH_INTERVAL 秒
BATCH_SIZE = 5
BATCH_INTERVAL = 0.2

# 并发采集线程数（1=串行，3=推荐，增大提速但增连接数）
MAX_WORKERS = 3
