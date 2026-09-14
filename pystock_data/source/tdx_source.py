"""
通达信数据源模块

功能：
- 封装 _tdxapi 库获取通达信数据
- 提供K线和分时数据获取接口
- 处理数据源异常
- 使用ClientManager避免客户端重复初始化

作者：PyStock项目组
日期：2026-09-13
版本：2.0.0
"""

import logging
import threading

import pandas as pd
from .client_manager import ClientManager
from .utils import standardize_fields, add_minute_fields, normalize_code_market

# 库内日志：默认静默，应用可通过配置logging启用
# propagate=False：隔离传播保证库内日志不外泄
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.propagate = False

# K线频率映射：旧freq参数 → _tdxapi period参数
# freq=9 日线 / 5 周线 / 6 月线（通达信标准category编码）
_FREQ_TO_PERIOD = {9: "1d", 5: "1w", 6: "1m"}


class TdxSource:
    """
    通达信数据源类

    功能：
        - 获取K线数据（日线、周线、月线）
        - 获取分时数据（分钟级）
        - 处理数据获取异常
        - 通过ClientManager管理client实例

    使用示例：
        >>> source = TdxSource()
        >>> df = source.fetch_bars('000400', 9, 100)
        >>> minute_df = source.fetch_minutes('000400', '20260624')

    参数说明：
        thread_safe: 是否使用线程独立 client
            - False（默认）：共享 client（TdxClient内置RLock，线程安全）
            - True：线程独立 client（多线程高并发场景用，减少锁竞争）

    性能优化：
        - 使用ClientManager缓存client实例
        - 避免重复初始化，节省资源

    Note:
        - 不直接持有client实例
        - 多个TdxSource实例共享同一个client（thread_safe=False时）
    """

    # 量比基准缓存：{(code, date, n): {'vol_list': list, 'prev_close': float}}
    # 指定date时基准数据固定不变，类级别共享（跨线程、跨实例复用，避免重复网络请求）
    _prev_day_vol_cache = {}
    _prev_day_vol_lock = threading.Lock()

    def __init__(self, market: str = 'std', thread_safe: bool = False):
        """
        初始化通达信数据源

        Args:
            market (str): 兼容旧签名的市场参数（默认'std'，实际市场按股票代码自动推断）
            thread_safe (bool): 是否使用线程独立 client
                - False（默认）：共享 client（TdxClient内置RLock保证线程安全）
                - True：线程独立 client（多线程高并发场景用）

        Note:
            - 不立即初始化client
            - client由ClientManager统一管理
            - 首次使用时通过ClientManager获取（懒加载）
        """
        self.market = market
        self.thread_safe = thread_safe

    def _get_client(self):
        """获取 client（根据 thread_safe 选择共享或线程独立）"""
        if self.thread_safe:
            return ClientManager.get_thread_client()
        return ClientManager.get_client()

    def fetch_bars(self, code: str, freq: int, offset: int) -> pd.DataFrame:
        """
        获取K线数据

        Args:
            code (str): 股票代码（6位字符串）
            freq (int): K线频率（9=日线, 5=周线, 6=月线）
            offset (int): 获取的数据数量

        Returns:
            DataFrame: K线数据（标准化后的DataFrame）

        Raises:
            Exception: 数据获取失败时抛出异常

        Example:
            >>> source = TdxSource()
            >>> day_df = source.fetch_bars('000400', 9, 100)  # 日线
            >>> week_df = source.fetch_bars('000400', 5, 100) # 周线
            >>> month_df = source.fetch_bars('000400', 6, 100) # 月线

        Note:
            - client通过ClientManager获取（缓存复用）
            - 首次调用时才初始化client（懒加载）
        """
        try:
            client = self._get_client()

            # 市场按股票代码自动推断（6→SH，0/3→SZ）
            _, market = normalize_code_market(code)
            period = _FREQ_TO_PERIOD.get(freq, "1d")

            # 单次请求上限800条，超过需分页拉取
            remaining = offset
            all_bars = []
            start = 0
            while remaining > 0:
                count = min(remaining, 800)
                bars = client.get_bars(code, market, period, count, start)
                if not bars:
                    break
                all_bars.extend(bars)
                remaining -= len(bars)
                start += len(bars)
                if len(bars) < count:
                    break

            if not all_bars:
                return pd.DataFrame()

            # 转DataFrame（Bar列表 → 标准行）
            records = [
                {
                    'datetime': b.datetime,
                    'open': b.open,
                    'close': b.close,
                    'high': b.high,
                    'low': b.low,
                    'volume': b.volume,
                    'amount': b.amount,
                }
                for b in all_bars
            ]
            df = pd.DataFrame(records)

            # 标准化字段（补 stock_code / trade_date / 列顺序）
            df = standardize_fields(df, code)

            return df

        except Exception as e:
            # 数据获取失败，返回空DataFrame
            logger.warning(f"[TdxSource] 获取K线数据失败: {e}")
            return pd.DataFrame()

    def fetch_minutes(self, code: str, date: str) -> pd.DataFrame:
        """
        获取分时数据

        Args:
            code (str): 股票代码（6位字符串）
            date (str): 日期（格式YYYYMMDD）

        Returns:
            DataFrame: 分时数据（包含hour和minute字段）

        Raises:
            Exception: 数据获取失败时抛出异常

        Example:
            >>> source = TdxSource()
            >>> minute_df = source.fetch_minutes('000400', '20260624')
            >>> # 包含字段：hour, minute

        Note:
            - client通过ClientManager获取（缓存复用）
            - 首次调用时才初始化client（懒加载）
        """
        try:
            # 通过ClientManager获取client（缓存复用）
            client = self._get_client()

            # 市场按股票代码自动推断
            _, market = normalize_code_market(code)

            # 历史分时（返回 [{price, volume}, ...]，时间轴为9:30~14:59共240分钟）
            mins = client.get_history_minute_time(code, market, int(date))

            if not mins:
                return pd.DataFrame()

            df = pd.DataFrame(mins)

            # 添加hour和minute字段（内部生成240分钟时间轴并标准化）
            df = add_minute_fields(df, code, date)

            return df

        except Exception as e:
            # 数据获取失败，返回空DataFrame
            logger.warning(f"[TdxSource] 获取分时数据失败: {e}")
            return pd.DataFrame()

    def fetch_realtime(self, codes: list) -> pd.DataFrame:
        """
        获取实时数据（扩展功能）

        Args:
            codes (list): 股票代码列表

        Returns:
            DataFrame: 实时数据

        Example:
            >>> source = TdxSource()
            >>> realtime_df = source.fetch_realtime(['000400', '000001'])
        """
        # TODO: 实现实时数据获取（可选扩展）
        raise NotImplementedError("实时数据获取功能待实现")

    def fetch_prev_n_day_vol(self, code: str, n: int = 5, date: str = None) -> dict:
        """
        获取过去n个交易日的日线成交量

        用于计算量比，需要过去n日的总成交量作为基准

        Args:
            code (str): 股票代码（6位字符串）
            n (int): 过去n个交易日，默认5
            date (str): 目标日期（格式YYYYMMDD），为None则取最新

        Returns:
            dict: {'vol_list': list, 'prev_close': float}
                vol_list: 过去n个交易日的成交量列表
                prev_close: 昨收价（目标日期前一交易日收盘价）

        Example:
            >>> source = TdxSource()
            >>> day_data = source.fetch_prev_n_day_vol('000400', n=5)
            >>> vol_list = day_data['vol_list']  # 过去5日成交量
            >>> avg_vol_per_minute = sum(vol_list) / (5 * 240)  # 分钟均量

        Note:
            - 获取足够多的日线数据确保覆盖目标日期
            - 如果指定date，取该日期前n日数据
            - 如果未指定date，取最新n日数据
            - 指定date时结果按 (code, date, n) 缓存，重复调用走缓存
        """
        # 缓存命中检查（仅指定date时缓存；未指定date取"最新"数据，盘中会变化，不缓存）
        if date is not None:
            cache_key = (code, date, n)
            with TdxSource._prev_day_vol_lock:
                if cache_key in TdxSource._prev_day_vol_cache:
                    return TdxSource._prev_day_vol_cache[cache_key]

        try:
            # 通过ClientManager获取client（缓存复用）
            client = self._get_client()
            _, market = normalize_code_market(code)

            # 多取一些数据确保能覆盖目标日期
            offset = n + 50 if date else n + 10
            # 分页拉取日线（单次上限800条）
            bars = client.get_bars(code, market, "1d", min(offset, 800), 0)

            if not bars:
                logger.warning(f"[TdxSource] 未获取到 {code} 的日线数据")
                return None

            # 转为DataFrame便于按日期定位
            df = pd.DataFrame(
                [
                    {
                        'datetime': b.datetime,
                        'close': b.close,
                        'volume': b.volume,
                    }
                    for b in bars
                ]
            )
            # _tdxapi 返回时间升序（旧在前，新在后），统一为时间倒序
            # （iloc[0]最新，便于头部对齐取最近n日）
            df = df.sort_values('datetime', ascending=False).reset_index(drop=True)

            if date:
                # 根据目标日期定位（只比较日期部分，忽略时间）
                target_date = pd.to_datetime(date, format='%Y%m%d').date()
                df['dt_parsed'] = pd.to_datetime(df['datetime']).dt.date
                mask = df['dt_parsed'] <= target_date

                if not mask.any():
                    logger.warning(f"[TdxSource] 日线数据不包含 {date} 之前的数据")
                    return None

                target_idx = df[mask].index[0]
                # 时间倒序：目标日期行 loc，其前一行（iloc[loc+1]）为前一交易日
                loc = df.index.get_loc(target_idx)

                if loc + 1 + n > len(df):
                    logger.warning(f"[TdxSource] {code} 在 {date} 之前数据不足 {n} 日")
                    return None

                # 过去n日：目标日期之前（更早）的n个交易日，按时间正序返回
                rows = df.iloc[loc + 1:loc + 1 + n]
                vol_list = rows['volume'].tolist()
                vol_list.reverse()

                # 昨收价：目标日期前一交易日收盘价（时间倒序中 loc+1 处）
                prev_close = float(df.iloc[loc + 1]['close'])
            else:
                # 未指定日期，取最新n日数据
                # 最新数据在index=0（时间倒序），取 [0, n) 即最近n日
                if len(df) < n + 1:
                    logger.warning(f"[TdxSource] {code} 日线数据不足 {n} 日")
                    return None

                rows = df.iloc[0:n]
                vol_list = rows['volume'].tolist()
                vol_list.reverse()

                # 昨收价：最新数据前一交易日收盘价（时间倒序中 index=1 处）
                prev_close = float(df.iloc[1]['close'])

            result = {'vol_list': vol_list, 'prev_close': prev_close}

            # 写入缓存（仅指定date时）
            if date is not None:
                with TdxSource._prev_day_vol_lock:
                    TdxSource._prev_day_vol_cache[(code, date, n)] = result

            return result

        except Exception as e:
            logger.warning(f"[TdxSource] 获取过去n日日线数据失败: {e}")
            return None