"""
新增指标类与特征编排的数值对拍测试

功能：
- BBI/ZXT/DZS/DZT/ZX 五组新指标类 vs tdx 公式直算参照
- extract_features 全量22特征 vs 上一版 tdx 直算实现（保证重构后数值零变化）

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import numpy as np
import pandas as pd
import pytest

from ..indicators import (
    BBIIndicator, ZXTIndicator, DZSIndicator, DZTIndicator,
    ZXShortTermTrendIndicator, ZXBullBearLineIndicator,
)
from ..indicators.tdx import (
    EMA, MA, SMA, HHV, LLV, KDJ, BBI, MACD,
)


def _make_kline(n=500, seed=11):
    """构造确定性K线测试数据（high严格大于low，trade_date为字符串列）"""
    np.random.seed(seed)
    close = 100 + np.cumsum(np.random.randn(n))
    spread = np.abs(np.random.randn(n)) + 0.5
    high = close + spread
    low = close - spread
    volume = np.random.randint(1000, 100000, n).astype(float)
    amount = volume * close
    dates = pd.date_range(end='2026-08-31', periods=n, freq='D').strftime('%Y-%m-%d')
    return pd.DataFrame({
        'trade_date': dates, 'open': close, 'close': close,
        'high': high, 'low': low, 'volume': volume, 'amount': amount,
    })


class TestBBIIndicator:
    def test_matches_tdx(self):
        df = _make_kline()
        result = BBIIndicator().calculate(df)
        assert np.allclose(result['bbi'].values, np.round(BBI(df['close'].values), 2), equal_nan=True)


class TestZXTIndicator:
    def test_matches_formula(self):
        df = _make_kline()
        result = ZXTIndicator().calculate(df)

        close, high, low = df['close'].values, df['high'].values, df['low'].values
        hhv4, llv4 = HHV(high, 4), LLV(low, 4)
        v1 = (hhv4 - close) / (hhv4 - llv4) * 100 - 90
        v2 = SMA(v1, 4, 1) + 100
        v3 = (close - llv4) / (hhv4 - llv4) * 100
        v4 = SMA(v3, 6, 1)
        v5 = SMA(v4, 6, 1) + 100
        expected = np.round(np.where(v5 - v2 > 4, v5 - v2 - 4, 0.0), 2)

        assert np.allclose(result['zxt'].values, expected, equal_nan=True)


class TestNeedleIndicators:
    def test_dzs_matches_formula(self):
        df = _make_kline()
        result = DZSIndicator().calculate(df)
        close, high, low = df['close'].values, df['high'].values, df['low'].values
        expected = np.round((close - LLV(low, 3)) / (HHV(close, 3) - LLV(low, 3)) * 100, 2)
        assert np.allclose(result['dzs'].values, expected, equal_nan=True)

    def test_dzt_matches_formula(self):
        df = _make_kline()
        result = DZTIndicator().calculate(df)
        close, high, low = df['close'].values, df['high'].values, df['low'].values
        expected = np.round((close - LLV(low, 21)) / (HHV(close, 21) - LLV(low, 21)) * 100, 2)
        assert np.allclose(result['dzt'].values, expected, equal_nan=True)


class TestZXIndicators:
    def test_short_term_trend_matches_formula(self):
        df = _make_kline()
        result = ZXShortTermTrendIndicator().calculate(df)
        expected = np.round(EMA(EMA(df['close'].values, 10), 10), 2)
        assert np.allclose(result['zx_short_term_trend'].values, expected, equal_nan=True)

    def test_bull_bear_line_matches_formula(self):
        df = _make_kline()
        result = ZXBullBearLineIndicator().calculate(df)
        close = df['close'].values
        expected = np.round(
            (MA(close, 14) + MA(close, 28) + MA(close, 57) + MA(close, 114)) / 4, 2)
        assert np.allclose(result['zx_bull_bear_line'].values, expected, equal_nan=True)


class TestExtractFeaturesParity:
    """extract_features（类式指标编排）vs 上一版 tdx 直算实现，全量22特征逐值对拍"""

    def test_matches_tdx_direct(self):
        from app.database.feature_import.feature_extractor import extract_features

        df = _make_kline()
        start_dt, end_dt = df['trade_date'].iloc[-5], df['trade_date'].iloc[-1]
        result = extract_features('000001', df, start_dt, end_dt)

        # 递推平滑（SMA/EMA）依赖全量历史，参照必须在全量序列上计算后取末5行
        close, high, low = df['close'].values, df['high'].values, df['low'].values

        # 上一版 tdx 直算参照
        K, D, J = KDJ(close, high, low)
        dif, dea, macd = MACD(close)
        hhv4, llv4 = HHV(high, 4), LLV(low, 4)
        v1 = (hhv4 - close) / (hhv4 - llv4) * 100 - 90
        v2 = SMA(v1, 4, 1) + 100
        v3 = (close - llv4) / (hhv4 - llv4) * 100
        v5 = SMA(SMA(v3, 6, 1), 6, 1) + 100

        expected = {
            'K': np.round(K, 2), 'D': np.round(D, 2), 'J': np.round(J, 2),
            'BBI': np.round(BBI(close), 2),
            'DIF': np.round(dif, 2), 'DEA': np.round(dea, 2), 'MACD': np.round(macd, 2),
            'zxt': np.round(np.where(v5 - v2 > 4, v5 - v2 - 4, 0.0), 2),
            'dzs': np.round((close - LLV(low, 3)) / (HHV(close, 3) - LLV(low, 3)) * 100, 2),
            'dzt': np.round((close - LLV(low, 21)) / (HHV(close, 21) - LLV(low, 21)) * 100, 2),
            'zx_short_term_trend': np.round(EMA(EMA(close, 10), 10), 2),
            'zx_bull_bear_line': np.round(
                (MA(close, 14) + MA(close, 28) + MA(close, 57) + MA(close, 114)) / 4, 2),
        }
        for n in [5, 7, 10, 20, 30, 40, 45, 60, 90, 250]:
            expected[f'MA{n}'] = np.round(MA(close, n), 2)

        assert len(result) == 5
        for col, exp_values in expected.items():
            assert np.allclose(result[col].values, exp_values[-5:], equal_nan=True), f'{col} 不一致'
