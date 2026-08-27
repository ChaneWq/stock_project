"""
MA7线上连续爬升选股器（MA7 Streak）计算模块

功能：
- 双模式 streak 计数：
    strict 严格模式：收盘价 > MA7，贴线跌破即断裂
    near 附近模式：收盘价在MA7上方，或跌破幅度 <= near_tolerance（贴线容错）
- streak 窗口质量指标：小阴小阳占比、平均日波动、MA7斜率、乖离度、最大回撤
- 入选判定 is_candidate（四条件：天数/小阴小阳占比/MA7向上/乖离上限）
- analyze_series 支持逐日回放，可复现任意历史日期的选股结果

设计文档：app/stock_selection/ma7_streak/设计方案.md
案例验证：002134（2026-08-04 突破站上MA7 → 小阴小阳爬升 → 2026-08-27 涨停）

作者：PyStock项目组
日期：2026-08-27
版本：1.0.0
"""

import math

import pandas as pd


class Ma7StreakSelector:
    """
    MA7线上连续爬升选股器

    功能：
        - 计算股价连续运行于MA7上方的天数（streak，双模式）
        - 评价 streak 窗口内的小阴小阳质量
        - 判定是否入选（is_candidate）

    使用示例：
        >>> sel = Ma7StreakSelector(mode='strict')          # 严格模式
        >>> sel_near = Ma7StreakSelector(mode='near')       # 附近模式（容差1%）
        >>> df = BasicBars().get_daily('002134', 120)       # 排序方式不限
        >>> summary = sel.analyze(df)                       # 最新交易日汇总 dict
        >>> series = sel.analyze_series(df)                 # 逐日回放 DataFrame

    逐日序列字段（analyze_series 输出，行顺序与输入一致）：
        ma7: MA7均线值
        pct: 涨跌幅(%)
        dev_pct: 收盘价对MA7偏离(%)
        above: 当日是否计为线上（按当前模式判定）
        streak: 截至当日的连续线上天数
        streak_start: streak起始日（无streak为None）
        small_candle_ratio: 窗口内小阴小阳占比（剔除首日，无窗口为NaN）
        avg_abs_pct: 窗口内平均日涨跌幅绝对值(%)
        ma7_slope_pct: 窗口内MA7涨幅(%)
        max_dd_pct: 窗口内收盘价距最高收盘的回撤(%)
        is_candidate: 是否入选

    汇总字段（analyze 输出 dict）：
        trade_date / close / ma7 / streak_days / streak_start /
        small_candle_ratio / avg_abs_pct / ma7_slope_pct / dev_pct /
        max_dd_pct / is_candidate

    注意：
        - 输入DataFrame必须包含close字段（trade_date可选，用于streak_start展示）
        - 输入排序方式不限（最新在前或最后在前均可，内部自动识别）
    """

    def __init__(self,
                 mode: str = 'strict',
                 near_tolerance: float = 0.01,
                 ma_period: int = 7,
                 min_streak_days: int = 5,
                 small_pct: float = 3.0,
                 min_small_ratio: float = 0.6,
                 max_dev_pct: float = 8.0,
                 exclude_first_day: bool = True):
        """
        初始化选股器

        Args:
            mode (str): 选股模式，'strict'（收盘>MA7）或 'near'（允许贴线容差），默认'strict'
            near_tolerance (float): 附近模式容差，跌破MA7幅度<=该值仍算线上（如0.01=1%）
            ma_period (int): 均线周期，默认7
            min_streak_days (int): 入选最小连续线上天数，默认5
            small_pct (float): 小阴小阳判定阈值（|涨跌幅|% <=），默认3.0
            min_small_ratio (float): 小阴小阳占比下限（剔除首日），默认0.6
            max_dev_pct (float): 收盘价对MA7最大偏离(%)，默认8.0
            exclude_first_day (bool): 质量指标是否剔除streak首日（突破大阳），默认True
        """
        if mode not in ('strict', 'near'):
            raise ValueError(f"mode 必须为 'strict' 或 'near'，当前: {mode}")
        if ma_period < 2:
            raise ValueError(f"ma_period 必须 >= 2，当前: {ma_period}")
        if near_tolerance < 0:
            raise ValueError(f"near_tolerance 不能为负，当前: {near_tolerance}")

        self.mode = mode
        self.near_tolerance = near_tolerance
        self.ma_period = ma_period
        self.min_streak_days = min_streak_days
        self.small_pct = small_pct
        self.min_small_ratio = min_small_ratio
        self.max_dev_pct = max_dev_pct
        self.exclude_first_day = exclude_first_day

    # ---------- 对外主接口 ----------

    def analyze(self, df: pd.DataFrame) -> dict:
        """
        单股汇总分析（以最新交易日为基准日）

        Args:
            df (DataFrame): 日线数据（需包含close，排序方式不限）

        Returns:
            dict: 汇总指标（见类docstring"汇总字段"），空数据返回 {}

        Example:
            >>> sel = Ma7StreakSelector()
            >>> summary = sel.analyze(BasicBars().get_daily('002134', 120))
            >>> print(summary['streak_days'], summary['is_candidate'])
        """
        if df is None or df.empty:
            return {}

        # 统一时间升序后取最后一行
        tmp = df.copy()
        if self._is_descending(tmp):
            tmp = tmp.iloc[::-1].reset_index(drop=True)
        series = self.analyze_series(tmp)
        if series.empty:
            return {}
        last = series.iloc[-1]

        return {
            'trade_date': self._value(last, 'trade_date'),
            'close': self._value(last, 'close'),
            'ma7': self._round(self._value(last, 'ma7')),
            'streak_days': int(last['streak']),
            'streak_start': self._value(last, 'streak_start'),
            'small_candle_ratio': self._round(self._value(last, 'small_candle_ratio')),
            'avg_abs_pct': self._round(self._value(last, 'avg_abs_pct')),
            'ma7_slope_pct': self._round(self._value(last, 'ma7_slope_pct')),
            'dev_pct': self._round(self._value(last, 'dev_pct')),
            'max_dd_pct': self._round(self._value(last, 'max_dd_pct')),
            'is_candidate': bool(last['is_candidate']),
        }

    def analyze_series(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        逐日回放分析（每天输出当日streak与窗口质量指标）

        Args:
            df (DataFrame): 日线数据（需包含close，排序方式不限）

        Returns:
            DataFrame: 原有字段 + 逐日评分列（见类docstring"逐日序列字段"），
            行顺序与输入一致

        Example:
            >>> sel = Ma7StreakSelector()
            >>> series = sel.analyze_series(df)
            >>> series[['trade_date', 'close', 'ma7', 'streak', 'is_candidate']]
        """
        if df is None or df.empty:
            return df.copy() if df is not None else df
        if 'close' not in df.columns:
            raise ValueError("输入DataFrame缺少必需字段: close")

        out = df.copy()
        reversed_input = self._is_descending(out)
        if reversed_input:
            out = out.iloc[::-1].reset_index(drop=True)

        close = out['close']
        ma = close.rolling(self.ma_period).mean()
        dev = (close - ma) / ma
        pct = close.pct_change() * 100

        # 模式判定：线上与否
        if self.mode == 'strict':
            above = close > ma
        else:  # near：跌破幅度 <= 容差仍算线上
            above = dev >= -self.near_tolerance
        above = above.fillna(False)

        # streak 计数：截至当日的连续线上天数
        n = len(out)
        streak = [0] * n
        cur = 0
        for i in range(n):
            cur = cur + 1 if bool(above.iloc[i]) else 0
            streak[i] = cur

        # 逐日窗口质量指标
        starts = [None] * n
        small_ratios = [float('nan')] * n
        avg_abses = [float('nan')] * n
        slopes = [float('nan')] * n
        max_dds = [float('nan')] * n
        candidates = [False] * n

        for i in range(n):
            s = streak[i]
            if s <= 0:
                continue
            start = i - s + 1
            starts[i] = self._date_str(out, start)

            # 质量窗口（可剔除首日突破大阳）
            win_pct = pct.iloc[start:i + 1]
            q_pct = win_pct.iloc[1:] if self.exclude_first_day else win_pct
            small_ratio = float('nan')
            avg_abs = float('nan')
            if len(q_pct) > 0:
                valid = q_pct.dropna()
                if len(valid) > 0:
                    small_ratio = float((valid.abs() <= self.small_pct).sum()) / len(valid)
                    avg_abs = float(valid.abs().mean())

            ma_start = float(ma.iloc[start])
            ma_end = float(ma.iloc[i])
            slope = (ma_end - ma_start) / ma_start * 100

            dev_i = float(dev.iloc[i]) * 100
            win_close = close.iloc[start:i + 1]
            win_max = float(win_close.max())
            max_dd = (win_max - float(close.iloc[i])) / win_max * 100

            is_cand = (s >= self.min_streak_days
                       and not math.isnan(small_ratio)
                       and small_ratio >= self.min_small_ratio
                       and slope > 0
                       and dev_i <= self.max_dev_pct)

            small_ratios[i] = small_ratio
            avg_abses[i] = avg_abs
            slopes[i] = slope
            max_dds[i] = max_dd
            candidates[i] = is_cand

        out['ma7'] = ma.round(4)
        out['pct'] = pct.round(2)
        out['dev_pct'] = (dev * 100).round(2)
        out['above'] = above
        out['streak'] = streak
        out['streak_start'] = starts
        out['small_candle_ratio'] = [round(v, 4) if not math.isnan(v) else v for v in small_ratios]
        out['avg_abs_pct'] = [round(v, 2) if not math.isnan(v) else v for v in avg_abses]
        out['ma7_slope_pct'] = [round(v, 2) if not math.isnan(v) else v for v in slopes]
        out['max_dd_pct'] = [round(v, 2) if not math.isnan(v) else v for v in max_dds]
        out['is_candidate'] = candidates

        # 恢复输入原顺序
        if reversed_input:
            out = out.iloc[::-1].reset_index(drop=True)
        return out

    # ---------- 内部方法 ----------

    def _is_descending(self, df: pd.DataFrame) -> bool:
        """判断DataFrame是否按时间倒序排列（最新在前）"""
        if len(df) < 2:
            return False
        for col in ('datetime', 'trade_date'):
            if col in df.columns:
                return df[col].iloc[0] > df[col].iloc[-1]
        return False

    def _date_str(self, df: pd.DataFrame, idx: int):
        """取指定行的日期（trade_date优先，无则返回行号）"""
        if 'trade_date' in df.columns:
            return df['trade_date'].iloc[idx]
        return idx

    @staticmethod
    def _value(row, field):
        """取行字段值，NaN转None"""
        if field not in row.index:
            return None
        v = row[field]
        if isinstance(v, float) and math.isnan(v):
            return None
        return v

    @staticmethod
    def _round(v, digits=2):
        """数值四舍五入，None保持None"""
        if v is None:
            return None
        return round(float(v), digits)
