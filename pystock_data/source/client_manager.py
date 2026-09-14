"""
客户端管理器模块

功能：
- 管理 _tdxapi.TdxClient 实例的创建和缓存
- 懒连接：首次获取时才连接服务器（含测速选优）
- 支持线程独立 client（get_thread_client）
- TdxClient 内置自动重连与心跳，无需在此重复实现

作者：PyStock项目组
日期：2026-09-13
版本：2.0.0
"""

import threading

from ._tdxapi import TdxClient


class ClientManager:
    """
    全局Client管理器

    功能：
        - 管理_tdxapi客户端实例
        - 缓存client避免重复初始化
        - 懒连接：首次get_client时才connect

    设计理念：
        - 单例缓存：全局只创建一个共享client
        - 线程独立：get_thread_client每线程一份
        - 连接管理交给TdxClient自身（内置RLock线程安全、自动重连、心跳）

    使用示例：
        >>> client = ClientManager.get_client()
        >>> client2 = ClientManager.get_client()  # 同一个实例

    性能优势：
        - 首次创建：测速选服务器 + 连接 + 三次握手
        - 后续获取：直接从缓存获取，0耗时
    """

    # 共享客户端实例（懒创建）
    _client = None
    # 共享实例创建锁（双重检查）
    _lock = threading.Lock()
    # 线程独立 client 存储（每个线程一份，互不影响）
    _thread_local = threading.local()

    @classmethod
    def get_client(cls) -> TdxClient:
        """
        获取或创建共享客户端

        Returns:
            TdxClient: 已连接的客户端实例（线程安全，内置RLock）

        实现机制：
            1. 首次调用：创建client并connect（自动测速选服务器）
            2. 后续调用：直接返回缓存实例

        Example:
            >>> client1 = ClientManager.get_client()
            >>> client2 = ClientManager.get_client()
            >>> assert client1 is client2  # 同一个实例

        Note:
            - TdxClient(heartbeat=True)启用30秒心跳保活
            - 请求失败时TdxClient自动重连重试
        """
        if cls._client is None:
            with cls._lock:
                if cls._client is None:
                    cls._client = TdxClient(heartbeat=True)
                    cls._client.connect()
        return cls._client

    @classmethod
    def get_thread_client(cls) -> TdxClient:
        """
        获取线程独立的客户端

        每个线程拥有独立的 client（基于 threading.local），
        避免多线程共享同一 socket 连接导致数据错乱。

        Returns:
            TdxClient: 当前线程专属的客户端实例

        实现机制：
            1. 首次调用（当前线程）：创建 client 并 connect
            2. 后续调用（同一线程）：直接返回该线程的 client

        Example:
            >>> # 在工作线程中
            >>> client = ClientManager.get_thread_client()
            >>> # 同一线程再次调用返回同一实例，不同线程返回不同实例

        Note:
            - 用于多线程并发采集场景
            - 每个线程的 client 独立，互不影响
            - 线程结束后 client 不自动释放（线程池复用线程时仍可用）
        """
        if not hasattr(cls._thread_local, 'client'):
            client = TdxClient(heartbeat=True)
            client.connect()
            cls._thread_local.client = client
        return cls._thread_local.client

    @classmethod
    def clear_cache(cls) -> None:
        """
        清空客户端缓存

        用途：
            - 测试时清理状态
            - 需要强制重新初始化时使用

        Example:
            >>> ClientManager.clear_cache()
            >>> # 下次get_client会重新创建client

        Note:
            - 一般情况下不需要调用此方法
            - 主要用于测试场景
        """
        with cls._lock:
            if cls._client is not None:
                try:
                    cls._client.close()
                except Exception:
                    pass
                cls._client = None
        if hasattr(cls._thread_local, 'client'):
            try:
                cls._thread_local.client.close()
            except Exception:
                pass
            del cls._thread_local.client

    @classmethod
    def get_cached_markets(cls) -> list:
        """
        获取已缓存的市场列表（兼容旧接口）

        Returns:
            list: 已缓存的市场标识列表

        Example:
            >>> ClientManager.get_client()
            >>> markets = ClientManager.get_cached_markets()
            >>> # ['std']

        用途：
            - 查看当前缓存状态
            - 监控和调试
        """
        markets = []
        if cls._client is not None:
            markets.append('std')
        return markets

    @classmethod
    def get_client_count(cls) -> int:
        """
        获取缓存中的client数量

        Returns:
            int: 缓存的client数量（共享1 + 当前线程独立1）

        Example:
            >>> ClientManager.get_client()
            >>> count = ClientManager.get_client_count()
            >>> # 1

        用途：
            - 监控缓存状态
            - 资源管理
        """
        count = 1 if cls._client is not None else 0
        if hasattr(cls._thread_local, 'client'):
            count += 1
        return count

    @classmethod
    def has_client(cls, market: str = 'std') -> bool:
        """
        检查client是否已缓存（兼容旧接口）

        Args:
            market (str): 兼容旧签名的市场参数（忽略）

        Returns:
            bool: 共享client是否已缓存

        Example:
            >>> ClientManager.get_client()
            >>> has = ClientManager.has_client()
            >>> # True

        用途：
            - 检查缓存状态
            - 预判断避免初始化开销
        """
        return cls._client is not None