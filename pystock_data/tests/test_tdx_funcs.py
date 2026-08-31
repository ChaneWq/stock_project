"""
通达信公式函数库测试模块

功能：
- 验证 tdx 子包可正常导入
- 数值对拍：MACD/KDJ/MA/EMA/SMA 等核心函数与 pandas 直接实现的参考结果一致

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import pytest
import numpy as np
import pandas as pd
from ..indicators.tdx import MACD, KDJ, MA, EMA, SMA, REF, HHV, LLV, CROSS, STD


class TestTdxFuncs:
    """
    序列原语函数测试

    测试范围：
        - MA/EMA/SMA 与 pandas 实现对拍
        - REF/HHV/LLV/STD 滚动窗口行为
        - CROSS 金叉判定
    """

    def setup_method(self):
        """
        测试初始化：构造确定性K线数据
        """
        np.random.seed(42)
        n = 200
        self.close = 100 + np.cumsum(np.random.randn(n))
        self.high = self.close + np.abs(np.random.randn(n))
        self.low = self.close - np.abs(np.random.randn(n))

    def test_ma(self):
        """MA 对拍 rolling mean（前 N-1 行为 NaN）"""
        result = MA(self.close, 5)
        expected = pd.Series(self.close).rolling(5).mean().values
        assert np.allclose(result[5:], expected[5:])
        assert np.isnan(result[:4]).all()

    def test_ema(self):
        """EMA 对拍 ewm(span=N, adjust=False)"""
        result = EMA(self.close, 12)
        expected = pd.Series(self.close).ewm(span=12, adjust=False).mean().values
        assert np.allclose(result, expected)

    def test_sma(self):
        """SMA(X,N,1) 对拍 ewm(alpha=1/N, adjust=False)"""
        result = SMA(self.close, 3, 1)
        expected = pd.Series(self.close).ewm(alpha=1/3, adjust=False).mean().values
        assert np.allclose(result, expected)

    def test_ref(self):
        """REF 序列下移 N"""
        result = REF(self.close, 2)
        assert np.isnan(result[:2]).all()
        assert np.allclose(result[2:], self.close[:-2])

    def test_hhv_llv(self):
        """HHV/LLV 对拍 rolling max/min"""
        assert np.allclose(HHV(self.high, 10)[10:], pd.Series(self.high).rolling(10).max().values[10:])
        assert np.allclose(LLV(self.low, 10)[10:], pd.Series(self.low).rolling(10).min().values[10:])

    def test_cross(self):
        """CROSS 上穿判定：S1 从下方穿越 S2 的位置为 True"""
        s1 = np.array([1.0, 2.0, 3.0, 2.0, 1.0])
        s2 = np.array([2.0, 2.0, 2.0, 2.0, 2.0])
        result = CROSS(s1, s2)
        assert result[2] == True and result.sum() == 1


class TestTdxIndicator:
    """
    具体指标函数测试

    测试范围：
        - MACD 与 pandas 直接实现对拍
        - KDJ 与手写实现对拍
    """

    def setup_method(self):
        """
        测试初始化：构造确定性K线数据
        """
        np.random.seed(42)
        n = 300
        self.close = 100 + np.cumsum(np.random.randn(n))
        self.high = self.close + np.abs(np.random.randn(n))
        self.low = self.close - np.abs(np.random.randn(n))

    def test_macd(self):
        """MACD 对拍 pandas 直接实现"""
        dif, dea, macd = MACD(self.close)
        s = pd.Series(self.close)
        exp_dif = s.ewm(span=12, adjust=False).mean() - s.ewm(span=26, adjust=False).mean()
        exp_dea = exp_dif.ewm(span=9, adjust=False).mean()
        exp_macd = 2 * (exp_dif - exp_dea)
        assert np.allclose(dif, exp_dif.values)
        assert np.allclose(dea, exp_dea.values)
        assert np.allclose(macd, exp_macd.values)

    def test_kdj(self):
        """KDJ 对拍通达信标准语义（前 N-1 行 NaN，SMA 从首个有效值递推）"""
        k, d, j = KDJ(self.close, self.high, self.low)
        # 参考实现：滚动窗口无 min_periods，RSV 前 8 行为 NaN
        low_n = pd.Series(self.low).rolling(9).min()
        high_n = pd.Series(self.high).rolling(9).max()
        rsv = (pd.Series(self.close) - low_n) / (high_n - low_n) * 100
        exp_k = rsv.ewm(alpha=1/3, adjust=False).mean()
        exp_d = exp_k.ewm(alpha=1/3, adjust=False).mean()
        exp_j = 3 * exp_k - 2 * exp_d
        assert np.allclose(k[9:], exp_k.values[9:])
        assert np.allclose(d[9:], exp_d.values[9:])
        assert np.allclose(j[9:], exp_j.values[9:])
