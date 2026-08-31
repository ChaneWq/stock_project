
-- flag标签
-- b2 倍量 涨停 红砖型
use gzqp_bigdata_dev;

insert into gzqp_bigdata_dev.s_f4
with stock_with_lag as (
    SELECT code, trade_date,
           LAG(trade_date, 1,'9999-99-99' ) OVER (PARTITION BY code ORDER BY trade_date) as prev1_trade_date,
           LAG(trade_date, 2, '9999-99-99') OVER (PARTITION BY code ORDER BY trade_date) as prev2_trade_date,
           lead(trade_date, 1, '9999-99-99') OVER (PARTITION BY code ORDER BY trade_date) as next1_trade_date,
           lead(trade_date, 2, '9999-99-99') OVER (PARTITION BY code ORDER BY trade_date) as next2_trade_date,
           open, close, high, low, vol, amount, zx_short_term_trend, zx_bull_bear_line, K, D, J, BBI, MA5, MA7, MA10, MA20, MA30, MA40, MA45, MA60, MA90, MA250, DIF, DEA, MACD, zxt, dzs, dzt,vol_ratio_0930, vol_ratio_0931, vol_ratio_0932, price_0930, price_0931, price_0932,
           LAG(close, 1, 0) OVER (PARTITION BY code ORDER BY trade_date) as prev1_close,
           LAG(high, 1, 0) OVER (PARTITION BY code ORDER BY trade_date) as prev1_high,
           LAG(low, 1, 0) OVER (PARTITION BY code ORDER BY trade_date) as prev1_low,
           LAG(vol, 1, 0) OVER (PARTITION BY code ORDER BY trade_date) as prev1_vol,
           LAG(close, 2, 0) OVER (PARTITION BY code ORDER BY trade_date) as prev2_close,
           LAG(high, 2, 0) OVER (PARTITION BY code ORDER BY trade_date) as prev2_high,
           LAG(low, 2, 0) OVER (PARTITION BY code ORDER BY trade_date) as prev2_low,
           LAG(vol, 2, 0) OVER (PARTITION BY code ORDER BY trade_date) as prev2_vol,
           LAG(zxt, 1, 0) OVER (PARTITION BY code ORDER BY trade_date) as prev1_zxt,
           LAG(zxt, 2, 0) OVER (PARTITION BY code ORDER BY trade_date) as prev2_zxt,
           lead(close, 1, NULL) OVER (PARTITION BY code ORDER BY trade_date) as next1_close,
           lead(high, 1, NULL) OVER (PARTITION BY code ORDER BY trade_date) as next1_high,
           lead(low, 1, NULL) OVER (PARTITION BY code ORDER BY trade_date) as next1_low,
           lead(vol, 1, 0) OVER (PARTITION BY code ORDER BY trade_date) as next1_vol,
           lead(close, 2, NULL) OVER (PARTITION BY code ORDER BY trade_date) as next2_close,
           lead(high, 2, NULL) OVER (PARTITION BY code ORDER BY trade_date) as next2_high,
           lead(low, 2, NULL) OVER (PARTITION BY code ORDER BY trade_date) as next2_low,
           lead(vol, 2, 0) OVER (PARTITION BY code ORDER BY trade_date) as next2_vol,
           LAG(J, 1, NULL) OVER (PARTITION BY code ORDER BY trade_date) as prev1_j,
           LAG(dzt, 1, NULL) OVER (PARTITION BY code ORDER BY trade_date) as prev1_dzt,
           LAG(dzt, 2, NULL) OVER (PARTITION BY code ORDER BY trade_date) as prev2_dzt,
           LAG(dzs, 1, NULL) OVER (PARTITION BY code ORDER BY trade_date) as prev1_dzs,
           LAG(dzs, 2, NULL) OVER (PARTITION BY code ORDER BY trade_date) as prev2_dzs
    FROM stock_features4
    where trade_date > date_sub(current_date(),20)
   -- and  code = '000400'
),
stock_with_lag2 as (
    select code, trade_date, prev1_trade_date, prev2_trade_date, next1_trade_date, next2_trade_date, open, close, high, low, vol, amount, zx_short_term_trend, zx_bull_bear_line, K, D, J, BBI, MA5, MA7, MA10, MA20, MA30, MA40, MA45, MA60, MA90, MA250, DIF, DEA, MACD, zxt, dzs, dzt,vol_ratio_0930, vol_ratio_0931, vol_ratio_0932, price_0930, price_0931, price_0932, prev1_close, prev1_high, prev1_low, prev1_vol, prev2_close, prev2_high, prev2_low, prev2_vol, prev1_zxt, prev2_zxt, next1_close, next1_high, next1_low, next1_vol, next2_close, next2_high, next2_low, next2_vol, prev1_j, prev1_dzt, prev2_dzt, prev1_dzs, prev2_dzs,
           round((prev1_close-prev2_close)/prev2_close*100,2) prev1_rate,
           round((next1_close-close)/close*100,2) next1_rate,
           round((next1_high-close)/close*100,2) next1_high_rate,
           round((close-prev1_close)/prev1_close*100,2) today_rate,
           case
               WHEN vol >= 2 * prev1_vol
                   AND close > prev1_close
                   THEN 1
               ELSE 0
               END as double_vol_f ,  -- 当天2倍量标志
           CASE
               WHEN code LIKE '30%' THEN
                   CASE WHEN close = high
                       AND ROUND((close - IFNULL(prev1_close, close)) / IFNULL(prev1_close, close) * 100, 2) >= 19.8
                            THEN 1 ELSE 0 END
               WHEN code LIKE '68%' THEN
                   CASE WHEN close = high
                       AND ROUND((close - IFNULL(prev1_close, close)) / IFNULL(prev1_close, close) * 100, 2) >= 19.8
                            THEN 1 ELSE 0 END
               ELSE
                   CASE WHEN close = high
                       AND ROUND((close - IFNULL(prev1_close, close)) / IFNULL(prev1_close, close) * 100, 2) >= 9.8
                            THEN 1 ELSE 0 END
               END AS zt_f,  -- 当天涨停标准
           if(zxt>prev2_zxt and prev1_zxt < prev2_zxt,1,0) zxt_f
    from stock_with_lag
),
stock_with_b2 as (
     SELECT
         code, trade_date, prev1_trade_date, prev2_trade_date, next1_trade_date, next2_trade_date, open, close, high, low, vol, amount, zx_short_term_trend, zx_bull_bear_line, K, D, J, BBI, MA5, MA7, MA10, MA20, MA30, MA40, MA45, MA60, MA90, MA250, DIF, DEA, MACD, zxt, dzs, dzt,vol_ratio_0930, vol_ratio_0931, vol_ratio_0932, price_0930, price_0931, price_0932, prev1_close, prev1_high, prev1_low, prev1_vol, prev2_close, prev2_high, prev2_low, prev2_vol, prev1_zxt, prev2_zxt, next1_close, next1_high, next1_low, next1_vol, next2_close, next2_high, next2_low, next2_vol, prev1_j, prev1_dzt, prev2_dzt, prev1_dzs, prev2_dzs, prev1_rate, next1_rate, next1_high_rate, today_rate, double_vol_f, zt_f, zxt_f,
         if(prev1_rate<0.8 and today_rate>4 and vol>prev1_vol and J<80 and close>prev1_high,1,0) b2_f
     from stock_with_lag2
)
select
    code, trade_date, prev1_trade_date, prev2_trade_date, next1_trade_date, next2_trade_date, open, close, high, low, vol, amount, zx_short_term_trend, zx_bull_bear_line, K, D, J, BBI, MA5, MA7, MA10, MA20, MA30, MA40, MA45, MA60, MA90, MA250, DIF, DEA, MACD, zxt, dzs, dzt,vol_ratio_0930, vol_ratio_0931, vol_ratio_0932, price_0930, price_0931, price_0932, prev1_close, prev1_high, prev1_low, prev1_vol, prev2_close, prev2_high, prev2_low, prev2_vol, prev1_zxt, prev2_zxt, next1_close, next1_high, next1_low, next1_vol, next2_close, next2_high, next2_low, next2_vol, prev1_j, prev1_dzt, prev2_dzt, prev1_dzs, prev2_dzs, prev1_rate, next1_rate, next1_high_rate, today_rate, double_vol_f, zt_f, zxt_f, b2_f,
       sum(double_vol_f) over (
           partition by code
           order by trade_date
           rows between 5 PRECEDING and current row
           ) as double_vol_f_d5,  -- 当天的前一日开始的5日内倍量数量(即：前一日、前二日、前三日、前四日、前五日)
       sum(double_vol_f) over (
           partition by code
           order by trade_date
           rows between 10 PRECEDING and current row
           ) as double_vol_f_d10, -- -- 当天的前一日开始的10日内倍量数量
       sum(zt_f) over (
           partition by code
           order by trade_date
           rows between 5 PRECEDING and current row
           ) as zt_f_d5,  -- 当天的前一日开始的5日内涨停数量
       sum(zt_f) over (
           partition by code
           order by trade_date
           rows between 10 PRECEDING and current row
           ) as zt_f_d10,  -- 当天的前一日开始的10日内涨停数量
        sum(b2_f) over (
            partition by code
            order by trade_date
            rows between 5 PRECEDING and current row
            ) as b2_f_d5,  -- 当天的前一日开始的5日内b2数量
        sum(b2_f) over (
            partition by code
            order by trade_date
            rows between 10 PRECEDING and current row
            ) as b2_f_d10  -- 当天的前一日开始的10日内b2数量
from stock_with_b2
where trade_date > date_sub(current_date(),10)
;


CREATE TABLE `s_f4` (
                        `code` varchar(10) NOT NULL ,
                        `trade_date` date NOT NULL ,
                        `prev1_trade_date` date NULL ,
                        `prev2_trade_date` date NULL ,
                        `next1_trade_date` date NULL ,
                        `next2_trade_date` date NULL ,
                        `open` decimal(10,3) NULL ,
                        `close` decimal(10,3) NULL ,
                        `high` decimal(10,3) NULL ,
                        `low` decimal(10,3) NULL ,
                        `vol` bigint NULL ,
                        `amount` bigint NULL ,
                        `zx_short_term_trend` decimal(10,3) NULL ,
                        `zx_bull_bear_line` decimal(10,3) NULL ,
                        `K` decimal(8,3) NULL ,
                        `D` decimal(8,3) NULL ,
                        `J` decimal(8,3) NULL ,
                        `BBI` decimal(10,3) NULL ,
                        `MA5` decimal(10,3) NULL ,
                        `MA7` decimal(10,3) NULL ,
                        `MA10` decimal(10,3) NULL ,
                        `MA20` decimal(10,3) NULL ,
                        `MA30` decimal(10,3) NULL ,
                        `MA40` decimal(10,3) NULL ,
                        `MA45` decimal(10,3) NULL ,
                        `MA60` decimal(10,3) NULL ,
                        `MA90` decimal(10,3) NULL ,
                        `MA250` decimal(10,3) NULL ,
                        `DIF` decimal(10,4) NULL ,
                        `DEA` decimal(10,4) NULL ,
                        `MACD` decimal(10,4) NULL ,
                        `zxt` decimal(10,3) NULL ,
                        `dzs` decimal(10,3) NULL ,
                        `dzt` decimal(10,3) NULL ,
                        `vol_ratio_0930` decimal(10,3) NULL ,
                        `vol_ratio_0931` decimal(10,3) NULL ,
                        `vol_ratio_0932` decimal(10,3) NULL ,
                        `price_0930` decimal(10,3) NULL ,
                        `price_0931` decimal(10,3) NULL ,
                        `price_0932` decimal(10,3) NULL ,
                        `prev1_close` decimal(10,3) NULL ,
                        `prev1_high` decimal(10,3) NULL ,
                        `prev1_low` decimal(10,3) NULL ,
                        `prev1_vol` bigint NULL ,
                        `prev2_close` decimal(10,3) NULL ,
                        `prev2_high` decimal(10,3) NULL ,
                        `prev2_low` decimal(10,3) NULL ,
                        `prev2_vol` bigint NULL ,
                        `prev1_zxt` decimal(10,3) NULL ,
                        `prev2_zxt` decimal(10,3) NULL ,
                        `next1_close` decimal(10,3) NULL ,
                        `next1_high` decimal(10,3) NULL ,
                        `next1_low` decimal(10,3) NULL ,
                        `next1_vol` bigint NULL ,
                        `next2_close` decimal(10,3) NULL ,
                        `next2_high` decimal(10,3) NULL ,
                        `next2_low` decimal(10,3) NULL ,
                        `next2_vol` bigint NULL ,
                        `prev1_j` decimal(8,3) NULL ,
                        `prev1_dzt` decimal(10,3) NULL ,
                        `prev2_dzt` decimal(10,3) NULL ,
                        `prev1_dzs` decimal(10,3) NULL ,
                        `prev2_dzs` decimal(10,3) NULL ,
                        `prev1_rate` decimal(8,4) NULL ,
                        `next1_rate` decimal(8,4) NULL ,
                        `next1_high_rate` decimal(8,4) NULL ,
                        `today_rate` decimal(8,4) NULL ,
                        `double_vol_f` tinyint NULL ,
                        `zt_f` tinyint NULL ,
                        `zxt_f` tinyint NULL ,
                        `b2_f` tinyint NULL ,
                        `double_vol_f_d5` bigint NULL ,
                        `double_vol_f_d10` bigint NULL ,
                        `zt_f_d5` bigint NULL ,
                        `zt_f_d10` bigint NULL ,
                        `b2_f_d5` bigint NULL ,
                        `b2_f_d10` bigint NULL
) ENGINE=OLAP
    UNIQUE KEY(`code`, `trade_date`)
DISTRIBUTED BY HASH(`code`) BUCKETS 10
PROPERTIES (
"replication_allocation" = "tag.location.default: 1",
"min_load_replica_num" = "-1",
"is_being_synced" = "false",
"storage_medium" = "hdd",
"storage_format" = "V2",
"inverted_index_storage_format" = "V1",
"compression" = "LZ4",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true",
"disable_auto_compaction" = "false",
"enable_single_replica_compaction" = "false",
"group_commit_interval_ms" = "10000",
"group_commit_data_bytes" = "134217728",
"enable_mow_light_delete" = "false"
);
