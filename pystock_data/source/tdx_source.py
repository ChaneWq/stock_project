"""
通达信数据源模块

功能：
- 封装mootdx库获取通达信数据
- 提供K线和分时数据获取接口
- 处理数据源异常
- 使用ClientManager避免客户端重复初始化

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import logging
import threading

import pandas as pd
from .client_manager import ClientManager
from .utils import standardize_fields, add_minute_fields

# 库内日志：默认静默，应用可通过配置logging启用
# propagate=False：第三方库(tdxpy等)可能调用basicConfig配置root logger，隔离传播保证库内日志不外泄
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())
logger.propagate = False


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
        market: 通达信市场参数，默认为'std'

    性能优化：
        - 使用ClientManager缓存client实例
        - 避免重复初始化，节省资源
        - 支持多市场配置

    Note:
        - 不直接持有client实例
        - 通过ClientManager.get_client获取缓存的client
        - 多个TdxSource实例共享同一个client（同market）
    """

    # 量比基准缓存：{(code, date, n): {'vol_list': list, 'prev_close': float}}
    # 指定date时基准数据固定不变，类级别共享（跨线程、跨实例复用，避免重复网络请求）
    _prev_day_vol_cache = {}
    _prev_day_vol_lock = threading.Lock()
    
    def __init__(self, market: str = 'std', thread_safe: bool = False):
        """
        初始化通达信数据源

        Args:
            market (str): 通达信市场参数，默认为'std'
            thread_safe (bool): 是否使用线程独立 client
                - False（默认）：共享 client（非线程安全，串行场景用）
                - True：线程独立 client（多线程并发场景用，基于 threading.local）

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
            return ClientManager.get_thread_client(self.market)
        return ClientManager.get_client(self.market)

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
            
            # 调用mootdx获取原始数据
            df = client.bars(symbol=code, frequency=freq, offset=offset)
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 标准化字段
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

            # 调用mootdx获取分时数据
            df = client.minutes(symbol=code, date=date)
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 添加hour和minute字段，传入date参数
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

            # 多取一些数据确保能覆盖目标日期
            offset = n + 50 if date else n + 10
            df = client.bars(symbol=code, frequency=9, offset=offset)  # 日线

            if df is None or df.empty:
                logger.warning(f"[TdxSource] 未获取到 {code} 的日线数据")
                return None

            if date:
                # 根据目标日期定位（只比较日期部分，忽略时间）
                target_date = pd.to_datetime(date, format='%Y%m%d').date()
                df['dt_parsed'] = pd.to_datetime(df['datetime']).dt.date
                mask = df['dt_parsed'] <= target_date

                if not mask.any():
                    logger.warning(f"[TdxSource] 日线数据不包含 {date} 之前的数据")
                    return None

                target_idx = df[mask].index[-1]
                # 取目标日期及之前 n+1 行
                loc = df.index.get_loc(target_idx)

                if loc < n:
                    logger.warning(f"[TdxSource] {code} 在 {date} 之前数据不足 {n} 日")
                    return None

                rows = df.iloc[loc - n:loc + 1]
                vol_list = rows['vol'].tolist()[:n]

                # 昨收价：目标日期前一交易日收盘价
                # 使用iloc访问，确保获取正确的行
                prev_close = float(rows.iloc[-2]['close'] if len(rows) >= 2 else rows.iloc[-1]['close'])
            else:
                # 未指定日期，取最新n日数据
                rows = df.iloc[-(n + 1):]
                vol_list = rows['vol'].tolist()[:n]

                # 昨收价：最新数据前一交易日收盘价
                prev_close = float(rows.iloc[-2]['close'] if len(rows) >= 2 else rows.iloc[-1]['close'])

            result = {'vol_list': vol_list, 'prev_close': prev_close}

            # 写入缓存（仅指定date时）
            if date is not None:
                with TdxSource._prev_day_vol_lock:
                    TdxSource._prev_day_vol_cache[(code, date, n)] = result

            return result

        except Exception as e:
            logger.warning(f"[TdxSource] 获取过去n日日线数据失败: {e}")
            return None