"""
检查mootdx返回的数据结构
"""
import pandas as pd
from mootdx.quotes import Quotes

# 创建数据源
client = Quotes.factory(market='std')

# 测试获取K线数据
print("=" * 50)
print("测试K线数据结构")
print("=" * 50)
bars_df = client.bars(symbol='000400', frequency=9, offset=5)

print("\n原始DataFrame信息:")
print(f"类型: {type(bars_df)}")
print(f"形状: {bars_df.shape}")
print(f"列名: {list(bars_df.columns)}")
print(f"索引: {bars_df.index}")
print(f"索引名: {bars_df.index.name}")

print("\n前5行数据:")
print(bars_df.head())

# 测试获取分时数据
print("\n" + "=" * 50)
print("测试分时数据结构")
print("=" * 50)
minutes_df = client.minutes(symbol='000400', date='20260624')

print("\n原始DataFrame信息:")
print(f"类型: {type(minutes_df)}")
print(f"形状: {minutes_df.shape}")
print(f"列名: {list(minutes_df.columns)}")
print(f"索引: {minutes_df.index}")
print(f"索引名: {minutes_df.index.name}")

print("\n前10行数据:")
print(minutes_df.head(10))