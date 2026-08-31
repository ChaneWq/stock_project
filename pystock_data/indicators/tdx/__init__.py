"""
通达信公式函数库

项目唯一的指标公式来源，提供通达信风格的公式函数：
- tdx_funcs: 序列原语（REF/HHV/LLV/MA/EMA/SMA/CROSS/BARSLAST 等）
- tdx_indicator: 具体指标函数（MACD/KDJ/RSI/ATR/DMI/BOLL 等）

用法：
    from pystock_data.indicators.tdx import MACD, KDJ, MA, EMA, CROSS

    dif, dea, macd = MACD(df['close'].values)          # 输入 numpy 数组
    k, d, j = KDJ(df['close'].values, df['high'].values, df['low'].values)
"""

from .tdx_funcs import *
from .tdx_indicator import *
