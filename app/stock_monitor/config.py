"""
性能优化配置

参数说明：
    BATCH_SIZE       : 批量采集大小，每采集 BATCH_SIZE 只后间隔一次
    BATCH_INTERVAL   : 批次之间的间隔（秒），防止请求过快触发限流
                       0 表示不间隔
    DAILY_CACHE_ENABLED : 是否启用日线数据缓存
                          日线数据日内不变（收盘后才更新），缓存后后续刷新无需重复请求
                          首次请求照常走网络，后续读缓存

间隔示例：
    BATCH_SIZE=5, BATCH_INTERVAL=0.2 → 25只 = 4批 × 0.2s = 0.8s 间隔
    BATCH_SIZE=1, BATCH_INTERVAL=0.1 → 退化为每只间隔0.1s（最保守）
    BATCH_SIZE=999, BATCH_INTERVAL=0  → 不间隔（最快，封禁风险高）
"""

# 批量采集间隔：每 BATCH_SIZE 只后间隔 BATCH_INTERVAL 秒
BATCH_SIZE = 5
BATCH_INTERVAL = 0.2

# 日线数据缓存（日内有效，避免重复请求）
DAILY_CACHE_ENABLED = True
