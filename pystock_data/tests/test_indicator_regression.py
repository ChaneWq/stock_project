"""
指标类回归测试模块（公式来源迁移到 tdx 库后的一致性验证）

功能：
- 用改造前的原始公式（pandas 直写）作为参照，逐值对拍改造后的指标类输出
- 确保 tdx 公式函数库替换自研公式后，历史数值行为零变化
- 保护下游依赖方（stock_monitor/minute_vr_scanner/examples 等）

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import numpy as np
import pandas as pd
import pytest
from ..indicators import MACDIndicator, KDJIndicator, MAIndicator, VolumeMAIndicator


def _make_kline(n=500, seed=7):
    """构造确定性K线测试数据"""
    np.random.seed(seed)
    close = 100 + np.cumsum(np.random.randn(n))
    high = close + np.abs(np.random.randn(n))
    low = close - np.abs(np.random.randn(n))
    volume = np.random.randint(1000, 100000, n).astype(float)
    return pd.DataFrame({'close': close, 'high': high, 'low': low, 'volume': volume})


class TestMACDRegression:
    """MACDIndicator：tdx.MACD vs 旧实现（ewm 直算）"""

    def test_macd_matches_legacy(self):
        df = _make_kline()
        result = MACDIndicator().calculate(df)

        # 旧实现参照（改造前 macd.py 的公式）
        ema_fast = df['close'].ewm(span=12, adjust=False).mean()
        ema_slow = df['close'].ewm(span=26, adjust=False).mean()
        exp_dif = ema_fast - ema_slow
        exp_dea = exp_dif.ewm(span=9, adjust=False).mean()
        exp_macd = 2 * (exp_dif - exp_dea)

        assert np.allclose(result['macd_dif'].values, exp_dif.round(2).values)
        assert np.allclose(result['macd_dea'].values, exp_dea.round(2).values)
        assert np.allclose(result['macd_macd'].values, exp_macd.round(2).values)


class TestKDJRegression:
    """KDJIndicator：tdx.LLV/HHV/SMA vs 旧实现（rolling min_periods=1 + ewm）"""

    def test_kdj_matches_legacy(self):
        df = _make_kline()
        result = KDJIndicator().calculate(df)

        # 旧实现参照（改造前 kdj.py 的公式）
        low_n = df['low'].rolling(9, min_periods=1).min()
        high_n = df['high'].rolling(9, min_periods=1).max()
        rsv = ((df['close'] - low_n) / (high_n - low_n) * 100).fillna(50)
        exp_k = rsv.ewm(com=2, adjust=False).mean()
        exp_d = exp_k.ewm(com=2, adjust=False).mean()
        exp_j = 3 * exp_k - 2 * exp_d

        assert np.allclose(result['kdj_k'].values, exp_k.round(2).values)
        assert np.allclose(result['kdj_d'].values, exp_d.round(2).values)
        assert np.allclose(result['kdj_j'].values, exp_j.round(2).values)


class TestMARegression:
    """MAIndicator：tdx.MA + expanding 补齐 vs 旧实现（rolling min_periods=1）"""

    @pytest.mark.parametrize('period', [5, 10, 20, 60])
    def test_ma_matches_legacy(self, period):
        df = _make_kline()
        result = MAIndicator(periods=[period]).calculate(df)

        # 旧实现参照（改造前 ma.py 的公式）
        expected = df['close'].rolling(period, min_periods=1).mean().round(2)
        assert np.allclose(result[f'ma{period}'].values, expected.values)


class TestVMASRegression:
    """VolumeMAIndicator：tdx.MA + expanding 补齐 vs 旧实现（rolling min_periods=1）"""

    @pytest.mark.parametrize('period', [5, 10])
    def test_vma_matches_legacy(self, period):
        df = _make_kline()
        result = VolumeMAIndicator(periods=[period]).calculate(df)

        # 旧实现参照（改造前 vma.py 的公式）
        expected = df['volume'].rolling(period, min_periods=1).mean().round(2)
        assert np.allclose(result[f'vma{period}'].values, expected.values)
