"""
客户端管理器模块

功能：
- 管理通达信客户端实例的创建和缓存
- 确保全局只有一个client实例，避免重复初始化
- 支持多市场配置

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

from mootdx.quotes import Quotes


class ClientManager:
    """
    全局Client管理器
    
    功能：
        - 管理通达信客户端实例
        - 缓存client避免重复初始化
        - 支持多市场配置
    
    设计理念：
        - 单例缓存：每个market只创建一次client
        - 全局共享：所有TdxSource实例共享client
        - 易于扩展：可添加连接池、健康检查等功能
    
    使用示例：
        >>> client = ClientManager.get_client('std')
        >>> client_std = ClientManager.get_client('std')  # 同一个实例
        
        >>> client_custom = ClientManager.get_client('custom')  # 不同实例
    
    性能优势：
        - 首次创建：正常初始化时间
        - 后续获取：直接从缓存获取，0耗时
        - 避免重复初始化：节省资源和网络开销
    """
    
    # 客户端缓存字典：{market: client_instance}
    _clients = {}
    
    @classmethod
    def get_client(cls, market: str = 'std') -> Quotes:
        """
        获取或创建客户端
        
        Args:
            market (str): 通达信市场参数，默认为'std'
        
        Returns:
            Quotes: 通达信客户端实例
        
        实现机制：
            1. 首次调用：创建client并缓存
            2. 后续调用：从缓存中获取（避免重复初始化）
        
        Example:
            >>> client1 = ClientManager.get_client('std')
            >>> client2 = ClientManager.get_client('std')
            >>> assert client1 is client2  # 同一个实例
        
        Note:
            - 同一个market只创建一次client
            - 不同market有不同client实例
        """
        # 如果缓存中不存在，创建并缓存
        if market not in cls._clients:
            cls._clients[market] = Quotes.factory(market=market)
        
        # 返回缓存的client
        return cls._clients[market]
    
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
        cls._clients.clear()
    
    @classmethod
    def get_cached_markets(cls) -> list:
        """
        获取已缓存的market列表
        
        Returns:
            list: 已缓存的market列表
        
        Example:
            >>> ClientManager.get_client('std')
            >>> ClientManager.get_client('custom')
            >>> markets = ClientManager.get_cached_markets()
            >>> # ['std', 'custom']
        
        用途：
            - 查看当前缓存状态
            - 监控和调试
        """
        return list(cls._clients.keys())
    
    @classmethod
    def get_client_count(cls) -> int:
        """
        获取缓存中的client数量
        
        Returns:
            int: 缓存的client数量
        
        Example:
            >>> ClientManager.get_client('std')
            >>> count = ClientManager.get_client_count()
            >>> # 1
        
        用途：
            - 监控缓存状态
            - 资源管理
        """
        return len(cls._clients)
    
    @classmethod
    def has_client(cls, market: str = 'std') -> bool:
        """
        检查指定market的client是否已缓存
        
        Args:
            market (str): 通达信市场参数
        
        Returns:
            bool: 是否已缓存
        
        Example:
            >>> ClientManager.get_client('std')
            >>> has_std = ClientManager.has_client('std')
            >>> # True
            >>> has_custom = ClientManager.has_client('custom')
            >>> # False
        
        用途：
            - 检查缓存状态
            - 预判断避免初始化开销
        """
        return market in cls._clients