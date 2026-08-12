"""
ClientManager性能优化示例

功能：
- 展示ClientManager避免重复初始化的效果
- 对比原实现和优化后的性能差异
- 展示多市场支持功能

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import sys
import os

# 添加项目路径到sys.path
project_path = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_path)

from pystock_data.basic import BasicBars, BasicMinutes
from pystock_data.source import ClientManager


def demo_problem_before_optimization():
    """
    演示1：优化前的问题分析
    
    展示原实现中频繁初始化client的问题
    """
    print("=" * 60)
    print("演示1：优化前的问题分析")
    print("=" * 60)
    
    print("\n问题场景：频繁创建基础数据实例")
    print("-" * 60)
    
    # 清空缓存（模拟原实现）
    ClientManager.clear_cache()
    
    print("\n创建3个BasicBars实例：")
    
    # 创建多个BasicBars实例
    bars1 = BasicBars()
    print(f"✅ bars1创建完成，ClientManager缓存: {ClientManager.get_client_count()}")
    
    bars2 = BasicBars()
    print(f"✅ bars2创建完成，ClientManager缓存: {ClientManager.get_client_count()}")
    
    bars3 = BasicBars()
    print(f"✅ bars3创建完成，ClientManager缓存: {ClientManager.get_client_count()}")
    
    # 获取数据验证client使用
    print("\n使用实例获取数据：")
    df1 = bars1.get_daily('000400', 10)
    print(f"✅ bars1获取数据成功，ClientManager缓存: {ClientManager.get_client_count()}")
    
    df2 = bars2.get_daily('000400', 10)
    print(f"✅ bars2获取数据成功，ClientManager缓存: {ClientManager.get_client_count()}")
    
    df3 = bars3.get_daily('000400', 10)
    print(f"✅ bars3获取数据成功，ClientManager缓存: {ClientManager.get_client_count()}")
    
    print("\n性能对比：")
    print(f"  原实现：3个BasicBars = 3个client实例（浪费资源）")
    print(f"  优化后：3个BasicBars = {ClientManager.get_client_count()}个client实例（共享高效）")


def demo_client_cache_and_reuse():
    """
    演示2：client缓存和复用机制
    
    展示ClientManager如何缓存和复用client实例
    """
    print("\n" + "=" * 60)
    print("演示2：client缓存和复用机制")
    print("=" * 60)
    
    # 清空缓存开始演示
    ClientManager.clear_cache()
    
    print("\n缓存机制验证：")
    print("-" * 60)
    
    # 首次获取client
    print("\n首次获取client（std market）：")
    client1 = ClientManager.get_client('std')
    print(f"✅ client1获取成功")
    print(f"  缓存数量: {ClientManager.get_client_count()}")
    print(f"  缓存列表: {ClientManager.get_cached_markets()}")
    
    # 再次获取client（应该复用）
    print("\n再次获取client（同一market）：")
    client2 = ClientManager.get_client('std')
    print(f"✅ client2获取成功")
    print(f"  缓存数量: {ClientManager.get_client_count()}（未增加）")
    print(f"  client1和client2是否相同: {client1 is client2}")
    
    # 获取不同market的client
    print("\n获取不同market的client：")
    client3 = ClientManager.get_client('custom')
    print(f"✅ client3获取成功（custom market）")
    print(f"  缓存数量: {ClientManager.get_client_count()}（增加1个）")
    print(f"  缓存列表: {ClientManager.get_cached_markets()}")
    print(f"  client1和client3是否相同: {client1 is client3}（不同实例）")


def demo_lazy_initialization():
    """
    演示3：懒加载机制
    
    展示client在首次使用时才初始化
    """
    print("\n" + "=" * 60)
    print("演示3：懒加载机制")
    print("=" * 60)
    
    # 清空缓存
    ClientManager.clear_cache()
    
    print("\n懒加载验证：")
    print("-" * 60)
    
    # 创建BasicBars实例
    print("\n创建BasicBars实例：")
    bars = BasicBars()
    print(f"✅ BasicBars创建完成")
    print(f"  ClientManager缓存数量: {ClientManager.get_client_count()}（尚未初始化）")
    
    # 获取数据时才初始化client
    print("\n首次获取数据（触发client初始化）：")
    df = bars.get_daily('000400', 10)
    print(f"✅ 数据获取成功，client已初始化")
    print(f"  ClientManager缓存数量: {ClientManager.get_client_count()}（已初始化）")
    
    # 再次获取数据（使用缓存client）
    print("\n再次获取数据（使用缓存client）：")
    df2 = bars.get_daily('000400', 20)
    print(f"✅ 数据获取成功，使用缓存client")
    print(f"  ClientManager缓存数量: {ClientManager.get_client_count()}（未增加）")


def demo_performance_comparison():
    """
    演示4：性能对比
    
    对比原实现和优化后的性能差异
    """
    print("\n" + "=" * 60)
    print("演示4：性能对比")
    print("=" * 60)
    
    # 清空缓存
    ClientManager.clear_cache()
    
    print("\n性能对比场景：获取100只股票数据")
    print("-" * 60)
    
    # 模拟获取100只股票数据
    stock_count = 10  # 为了演示简化为10只
    
    print(f"\n模拟获取{stock_count}只股票的日线数据：")
    
    # 创建多个BasicBars实例（模拟批量处理）
    bars_list = []
    for i in range(stock_count):
        bars_list.append(BasicBars())
    
    print(f"✅ 创建{stock_count}个BasicBars实例完成")
    print(f"  ClientManager缓存数量: {ClientManager.get_client_count()}（只有1个）")
    
    # 获取数据
    for i, bars in enumerate(bars_list):
        df = bars.get_daily('000400', 10)
    
    print(f"✅ 所有数据获取完成")
    print(f"  ClientManager缓存数量: {ClientManager.get_client_count()}（仍为1个）")
    
    print("\n性能分析：")
    print(f"  原实现（无缓存）：")
    print(f"    - {stock_count}个实例 = {stock_count}次client初始化")
    print(f"    - 资源浪费，性能开销")
    
    print(f"  优化后（ClientManager）：")
    print(f"    - {stock_count}个实例 = 1次client初始化（首次使用）")
    print(f"    - 后续{stock_count-1}次复用缓存client")
    print(f"    - 节省资源，性能提升")


def demo_client_manager_utilities():
    """
    演示5：ClientManager工具方法
    
    展示缓存管理、状态查询等功能
    """
    print("\n" + "=" * 60)
    print("演示5：ClientManager工具方法")
    print("=" * 60)
    
    # 清空缓存开始
    ClientManager.clear_cache()
    
    print("\n缓存管理工具：")
    print("-" * 60)
    
    # 创建缓存
    ClientManager.get_client('std')
    ClientManager.get_client('custom')
    
    print(f"\n当前缓存状态：")
    print(f"  缓存数量: {ClientManager.get_client_count()}")
    print(f"  缓存列表: {ClientManager.get_cached_markets()}")
    
    # 检查缓存状态
    print(f"\n检查缓存状态：")
    print(f"  has_client('std'): {ClientManager.has_client('std')}")
    print(f"  has_client('custom'): {ClientManager.has_client('custom')}")
    print(f"  has_client('other'): {ClientManager.has_client('other')}")
    
    # 清空缓存
    print(f"\n清空缓存：")
    ClientManager.clear_cache()
    print(f"  ✅ 缓存已清空")
    print(f"  缓存数量: {ClientManager.get_client_count()}")
    print(f"  缓存列表: {ClientManager.get_cached_markets()}")


def main():
    """运行所有演示"""
    print("\n" + "=" * 60)
    print("ClientManager性能优化演示")
    print("=" * 60)
    
    try:
        demo_problem_before_optimization()
        demo_client_cache_and_reuse()
        demo_lazy_initialization()
        demo_performance_comparison()
        demo_client_manager_utilities()
        
        print("\n" + "=" * 60)
        print("✅ 所有演示完成！")
        print("=" * 60)
        
        print("\n关键特性总结：")
        print("1. **避免重复初始化**：多个实例共享同一个client")
        print("2. **懒加载机制**：首次使用时才初始化")
        print("3. **缓存复用**：后续使用直接从缓存获取")
        print("4. **多市场支持**：不同market有不同client")
        print("5. **全局管理**：统一管理，易于监控")
        print("6. **性能提升**：节省资源，提高效率")
        
        print("\n适用场景：")
        print("- 批量获取多只股票数据")
        print("- 频繁创建基础数据实例")
        print("- 组合使用多个基础类")
        print("- 策略应用中数据获取")
        
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()