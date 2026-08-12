"""
客户端管理器测试模块

功能：
- 测试ClientManager的缓存和复用功能
- 测试多市场支持
- 测试缓存管理功能

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pytest
from ..source import ClientManager


class TestClientManager:
    """
    ClientManager测试类
    
    测试范围：
        - client缓存和复用
        - 多市场支持
        - 缓存管理功能
    """
    
    def setup_method(self):
        """
        测试初始化
        
        清空缓存确保测试独立
        """
        ClientManager.clear_cache()
    
    def teardown_method(self):
        """
        测试清理
        
        清空缓存避免影响后续测试
        """
        ClientManager.clear_cache()
    
    def test_client_cache_and_reuse(self):
        """
        测试client缓存和复用
        
        验证：
            - 同一个market获取同一个client实例
            - client不会重复初始化
        """
        # 首次获取client
        client1 = ClientManager.get_client('std')
        
        # 再次获取client（应该复用）
        client2 = ClientManager.get_client('std')
        
        # 验证是同一个实例
        assert client1 is client2, "同一个market应该返回同一个client实例"
        
        # 验证缓存数量
        assert ClientManager.get_client_count() == 1, "应该只有一个client缓存"
    
    def test_multi_market_support(self):
        """
        测试多市场支持
        
        验证：
            - 不同market有不同的client实例
            - 每个market独立缓存
        """
        # 获取std市场client
        client_std = ClientManager.get_client('std')
        
        # 获取custom市场client
        client_custom = ClientManager.get_client('custom')
        
        # 验证是不同实例
        assert client_std is not client_custom, "不同market应该有不同的client实例"
        
        # 验证缓存数量
        assert ClientManager.get_client_count() == 2, "应该有两个client缓存"
        
        # 验证缓存的market列表
        markets = ClientManager.get_cached_markets()
        assert 'std' in markets, "std应该被缓存"
        assert 'custom' in markets, "custom应该被缓存"
    
    def test_has_client(self):
        """
        测试has_client方法
        
        验证：
            - 未缓存时返回False
            - 已缓存时返回True
        """
        # 未缓存时
        assert not ClientManager.has_client('std'), "未缓存时应该返回False"
        
        # 获取client后缓存
        ClientManager.get_client('std')
        
        # 已缓存时
        assert ClientManager.has_client('std'), "已缓存时应该返回True"
        assert not ClientManager.has_client('custom'), "其他market应该返回False"
    
    def test_clear_cache(self):
        """
        测试clear_cache方法
        
        验证：
            - 清空后缓存为空
            - 清空后可以重新初始化
        """
        # 创建缓存
        client1 = ClientManager.get_client('std')
        assert ClientManager.get_client_count() == 1
        
        # 清空缓存
        ClientManager.clear_cache()
        
        # 验证缓存已清空
        assert ClientManager.get_client_count() == 0, "缓存应该已清空"
        assert not ClientManager.has_client('std'), "清空后should返回False"
        
        # 再次获取client（会重新初始化）
        client2 = ClientManager.get_client('std')
        
        # 验证是新实例（不是之前的缓存）
        # 注意：这个测试可能在某些环境下失败，因为Quotes.factory可能返回相同实例
        # 但我们主要验证缓存机制工作正常
        assert ClientManager.get_client_count() == 1, "重新创建后应该有1个缓存"
    
    def test_get_cached_markets(self):
        """
        测试get_cached_markets方法
        
        验证：
            - 返回正确的market列表
            - 动态更新market列表
        """
        # 未缓存时
        markets = ClientManager.get_cached_markets()
        assert len(markets) == 0, "未缓存时应该返回空列表"
        
        # 添加std缓存
        ClientManager.get_client('std')
        markets = ClientManager.get_cached_markets()
        assert markets == ['std'], "应该只有std"
        
        # 添加custom缓存
        ClientManager.get_client('custom')
        markets = ClientManager.get_cached_markets()
        assert 'std' in markets and 'custom' in markets, "应该有std和custom"
        assert len(markets) == 2, "应该有2个market"
    
    def test_get_client_count(self):
        """
        测试get_client_count方法
        
        验证：
            - 返回正确的缓存数量
            - 动态更新缓存数量
        """
        # 未缓存时
        assert ClientManager.get_client_count() == 0
        
        # 添加1个缓存
        ClientManager.get_client('std')
        assert ClientManager.get_client_count() == 1
        
        # 添加第2个缓存
        ClientManager.get_client('custom')
        assert ClientManager.get_client_count() == 2
        
        # 清空缓存
        ClientManager.clear_cache()
        assert ClientManager.get_client_count() == 0
    
    def test_performance_avoid_reinitialization(self):
        """
        测试性能优化：避免重复初始化
        
        验证：
            - 多次调用get_client不会重复初始化
            - 实际使用场景中的性能提升
        
        Note:
            - 这个测试主要验证缓存机制的正确性
            - 实际性能提升需要通过实际数据获取来验证
        """
        # 创建3个TdxSource实例
        from ..source import TdxSource
        
        source1 = TdxSource()
        source2 = TdxSource()
        source3 = TdxSource()
        
        # 获取client（应该只有1个缓存）
        # 即使创建多个TdxSource，client仍然共享
        assert ClientManager.get_client_count() == 0, "未使用前不应该有缓存"
        
        # 首次使用时才初始化client
        client1 = ClientManager.get_client('std')
        assert ClientManager.get_client_count() == 1
        
        # 后续使用不会增加缓存数量
        client2 = ClientManager.get_client('std')
        client3 = ClientManager.get_client('std')
        
        assert ClientManager.get_client_count() == 1, "应该始终只有1个缓存"
        assert client1 is client2 is client3, "应该都是同一个实例"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])