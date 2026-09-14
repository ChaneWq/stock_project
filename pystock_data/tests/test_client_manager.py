"""
客户端管理器测试模块

功能：
- 测试ClientManager的缓存和复用功能
- 测试线程独立client
- 测试缓存管理功能

作者：PyStock项目组
日期：2026-09-13
版本：2.0.0
"""

import threading

import pytest
from ..source import ClientManager


class TestClientManager:
    """
    ClientManager测试类

    测试范围：
        - client缓存和复用
        - 线程独立client
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
            - 多次获取返回同一个client实例
            - client不会重复初始化
        """
        # 首次获取client
        client1 = ClientManager.get_client()

        # 再次获取client（应该复用）
        client2 = ClientManager.get_client()

        # 验证是同一个实例
        assert client1 is client2, "多次获取应该返回同一个client实例"

        # 验证缓存数量
        assert ClientManager.get_client_count() == 1, "应该只有一个client缓存"

    def test_thread_client_independence(self):
        """
        测试线程独立client

        验证：
            - 不同线程获取不同client实例
            - 同一线程内复用同一实例
        """
        main_client = ClientManager.get_thread_client()

        # 同一线程再次获取，应为同一实例
        assert ClientManager.get_thread_client() is main_client

        # 子线程获取，应为不同实例
        sub_clients = []

        def worker():
            sub_clients.append(ClientManager.get_thread_client())

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert len(sub_clients) == 1
        assert sub_clients[0] is not main_client, "不同线程应该是不同client实例"

        # 清理子线程client
        sub_clients[0].close()

    def test_thread_client_separate_from_shared(self):
        """
        测试线程独立client与共享client相互独立
        """
        shared = ClientManager.get_client()
        thread_cli = ClientManager.get_thread_client()

        assert shared is not thread_cli, "共享与线程独立client应为不同实例"
        assert ClientManager.get_client_count() == 2, "应有2个client缓存"

        thread_cli.close()

    def test_has_client(self):
        """
        测试has_client方法

        验证：
            - 未缓存时返回False
            - 已缓存时返回True
        """
        # 未缓存时
        assert not ClientManager.has_client(), "未缓存时应该返回False"

        # 获取client后缓存
        ClientManager.get_client()

        # 已缓存时
        assert ClientManager.has_client(), "已缓存时应该返回True"

    def test_clear_cache(self):
        """
        测试clear_cache方法

        验证：
            - 清空后缓存为空
            - 清空后可以重新初始化
        """
        # 创建缓存
        ClientManager.get_client()
        assert ClientManager.get_client_count() == 1

        # 清空缓存
        ClientManager.clear_cache()

        # 验证缓存已清空
        assert ClientManager.get_client_count() == 0, "缓存应该已清空"
        assert not ClientManager.has_client(), "清空后应该返回False"

        # 再次获取client（会重新初始化）
        client2 = ClientManager.get_client()

        # 验证重新创建成功
        assert ClientManager.get_client_count() == 1, "重新创建后应该有1个缓存"
        assert client2 is not None

    def test_get_cached_markets(self):
        """
        测试get_cached_markets方法

        验证：
            - 未缓存时返回空列表
            - 缓存后包含std标识
        """
        # 未缓存时
        markets = ClientManager.get_cached_markets()
        assert len(markets) == 0, "未缓存时应该返回空列表"

        # 添加缓存
        ClientManager.get_client()
        markets = ClientManager.get_cached_markets()
        assert markets == ['std'], "应该只有std"

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
        ClientManager.get_client()
        assert ClientManager.get_client_count() == 1

        # 清空缓存
        ClientManager.clear_cache()
        assert ClientManager.get_client_count() == 0

    def test_performance_avoid_reinitialization(self):
        """
        测试性能优化：避免重复初始化

        验证：
            - 多次调用get_client不会重复初始化
            - 实际使用场景中的性能提升
        """
        # 创建3个TdxSource实例
        from ..source import TdxSource

        source1 = TdxSource()
        source2 = TdxSource()
        source3 = TdxSource()

        # 未使用前不应该有缓存
        assert ClientManager.get_client_count() == 0, "未使用前不应该有缓存"

        # 首次使用时才初始化client
        client1 = ClientManager.get_client()
        assert ClientManager.get_client_count() == 1

        # 后续使用不会增加缓存数量
        client2 = ClientManager.get_client()
        client3 = ClientManager.get_client()

        assert ClientManager.get_client_count() == 1, "应该始终只有1个缓存"
        assert client1 is client2 is client3, "应该都是同一个实例"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])