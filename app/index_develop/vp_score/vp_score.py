"""
量价打分指标（VP Score）计算模块

功能：
- Layer1 单日量价分 day_score：涨跌方向分 + 量价配合分（缩量下跌为正分）
- Layer2 形态累计分 pattern_score：状态机跟踪"爆量信号→缩量回调→放量启动"
- 输出逐日状态（SEARCHING/SIGNAL/PULLBACK/CONFIRMED/EXPIRED）与关键事件

设计文档：app/index_develop/vp_score/设计方案.md
案例验证：000592（2026-08-18 爆量 → 08-21/08-24 缩量枯竭 → 08-25 启动 → 08-27 涨停）

作者：PyStock项目组
日期：2026-08-27
版本：1.0.0
"""

import pandas as pd

from pystock_data.indicators.base import IndicatorBase


class VPScoreIndicator(IndicatorBase):
    """
    量价打分指标计算类

    功能：
        - 单日量价打分（day_score，-100 ~ +100）
        - 形态累计打分（pattern_score，状态机）
        - 标记爆量信号 / 极度缩量 / 启动确认 / 形态失败 / 形态过期事件

    使用示例：
        >>> vps = VPScoreIndicator()
        >>> df = BasicBars().get_daily('000592', 120)   # 最新在前或正序均可
        >>> result = vps.calculate(df)
        >>> result[['trade_date', 'day_score', 'state', 'pattern_score']]

    追加字段：
        pct: 涨跌幅(%)
        vr5: 量比（当日量 / 前5日平均量，不含当日）
        day_score: 单日量价分（-100 ~ +100）
        state: SEARCHING / SIGNAL / PULLBACK / CONFIRMED / EXPIRED
        shrink_ratio: 当日量 / 信号日量（无形态时为 NaN）
        pattern_score: 形态累计分（无形态时为 0）
        event: 爆量信号 / 极度缩量 / 启动确认 / 形态失败 / 形态过期 / 形态结束

    下游信号约定：
        - state == 'PULLBACK' 且 pattern_score >= watch_score  → 蓄势预警
        - state == 'CONFIRMED'（首次出现）                      → 启动信号

    注意：
        - 输入DataFrame必须包含 open/high/low/close/volume 字段
        - 输入排序方式不限（最新在前或最后在前均可，内部自动识别）
        - 输出保持与输入相同的行顺序
    """

    # ---------- 固定分值表（细粒度加减分项，集中定义） ----------
    _SIGNAL_BASE = 60       # 信号日初始形态分
    _CONFIRM_BONUS = 25     # 启动确认加分
    _CONTINUE_BONUS = 10    # 确认后加速上攻加分
    _DECAY_PER_DAY = 15     # 回调超时每日衰减分
    _CONVERGE_BONUS = 3     # 跌幅收敛加分

    def __init__(self,
                 vr_signal: float = 2.0,
                 pct_signal: float = 3.0,
                 vr_strong: float = 3.0,
                 pct_strong: float = 1.0,
                 shrink_levels: tuple = (0.3, 0.5, 0.8),
                 max_pullback_days: int = 10,
                 rebound_pct: float = 3.0,
                 rebound_vol_ratio: float = 1.3,
                 fail_pct: float = -5.0,
                 fail_vol_ratio: float = 0.8,
                 watch_score: int = 80):
        """
        初始化量价打分指标

        Args:
            vr_signal (float): 信号日量比下限，默认2.0
            pct_signal (float): 信号日涨幅下限(%)，默认3.0
            vr_strong (float): 强信号量比下限（满足时涨幅要求放宽至pct_strong），默认3.0
            pct_strong (float): 强信号涨幅下限(%)，默认1.0
            shrink_levels (tuple): 缩量分档阈值（极度/明显/温和），默认(0.3, 0.5, 0.8)
            max_pullback_days (int): 回调蓄势期上限（交易日），默认10
            rebound_pct (float): 启动确认涨幅下限(%)，默认3.0
            rebound_vol_ratio (float): 启动日量/前日量下限，默认1.3
            fail_pct (float): 放量暴跌终止线(%)，默认-5.0
            fail_vol_ratio (float): 暴跌终止的量能线（×信号日量），默认0.8
            watch_score (int): 蓄势预警分数线，默认80
        """
        super().__init__(name='VPScore', required_fields=['open', 'high', 'low', 'close', 'volume'])
        self.vr_signal = vr_signal
        self.pct_signal = pct_signal
        self.vr_strong = vr_strong
        self.pct_strong = pct_strong
        self.shrink_levels = shrink_levels
        self.max_pullback_days = max_pullback_days
        self.rebound_pct = rebound_pct
        self.rebound_vol_ratio = rebound_vol_ratio
        self.fail_pct = fail_pct
        self.fail_vol_ratio = fail_vol_ratio
        self.watch_score = watch_score

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算量价打分

        Args:
            df (DataFrame): 日线数据（需包含 open/high/low/close/volume，
                排序方式不限，BasicBars.get_daily 的倒序输出可直接传入）

        Returns:
            DataFrame: 原有字段 + pct/vr5/day_score/state/shrink_ratio/pattern_score/event，
            行顺序与输入一致

        Example:
            >>> vps = VPScoreIndicator()
            >>> result = vps.calculate(BasicBars().get_daily('000592', 120))
        """
        if not self.validate_input(df):
            return df.copy()

        out = df.copy()

        # 统一转为时间升序计算（兼容最新在前/在后两种输入）
        reversed_input = self._is_descending(out)
        if reversed_input:
            out = out.iloc[::-1].reset_index(drop=True)

        # 基础派生列：涨跌幅、量比
        out['pct'] = (out['close'].pct_change() * 100).round(2)
        out['vr5'] = (out['volume'] / out['volume'].rolling(5).mean().shift(1)).round(2)

        n = len(out)
        day_scores = [0] * n
        states = ['SEARCHING'] * n
        shrinks = [float('nan')] * n
        patterns = [0] * n
        events = [''] * n

        # 状态机内部变量
        phase = 'SEARCHING'      # SEARCHING / PULLBACK / CONFIRMED
        score = 0                # 形态累计分
        vol_s = None             # 信号日成交量
        close_s = None           # 信号日收盘价
        pullback_days = 0        # 回调期已过交易日数
        confirm_days = 0         # 确认后已过交易日数

        for i in range(n):
            pct = out['pct'].iloc[i]
            pct = 0.0 if pd.isna(pct) else float(pct)
            vr5 = out['vr5'].iloc[i]
            vr5 = float('nan') if pd.isna(vr5) else float(vr5)
            vol = float(out['volume'].iloc[i])
            close = float(out['close'].iloc[i])
            prev_vol = float(out['volume'].iloc[i - 1]) if i > 0 else None
            if i > 0 and not pd.isna(out['pct'].iloc[i - 1]):
                prev_abs_pct = abs(float(out['pct'].iloc[i - 1]))
            else:
                prev_abs_pct = None

            # Layer1: 单日量价分（与形态无关，每日必算）
            day_scores[i] = self._calc_day_score(pct, vr5)

            ev = ''
            if phase == 'SEARCHING':
                if self._is_signal(pct, vr5):
                    # 爆量信号日：进入回调蓄势期
                    phase = 'PULLBACK'
                    score = self._SIGNAL_BASE
                    vol_s, close_s = vol, close
                    pullback_days = 0
                    states[i] = 'SIGNAL'
                    patterns[i] = score
                    shrinks[i] = 1.0
                    ev = '爆量信号'
                # 无信号：保持默认（SEARCHING / 0分）

            elif phase == 'PULLBACK':
                pullback_days += 1
                shrink = vol / vol_s
                shrinks[i] = round(shrink, 4)
                states[i] = 'PULLBACK'

                if pct <= self.fail_pct and vol >= self.fail_vol_ratio * vol_s:
                    # 放量暴跌：形态失败
                    score = 0
                    phase = 'SEARCHING'
                    states[i] = 'EXPIRED'
                    ev = '形态失败'
                elif pct >= self.rebound_pct and prev_vol is not None \
                        and vol >= self.rebound_vol_ratio * prev_vol:
                    # 放量上涨：启动确认
                    score += self._CONFIRM_BONUS
                    phase = 'CONFIRMED'
                    confirm_days = 0
                    states[i] = 'CONFIRMED'
                    ev = '启动确认'
                elif pullback_days > self.max_pullback_days:
                    # 回调超时：逐日衰减至0后过期
                    score = max(0, score - self._DECAY_PER_DAY)
                    if score == 0:
                        phase = 'SEARCHING'
                        states[i] = 'EXPIRED'
                        ev = '形态过期'
                else:
                    # 正常回调蓄势：缩量/跌幅/收敛/深度 四项加减分
                    delta = self._pullback_delta(pct, shrink, close / close_s - 1, prev_abs_pct)
                    score += delta
                    if shrink <= self.shrink_levels[0]:
                        ev = '极度缩量'
                patterns[i] = score

            else:  # phase == 'CONFIRMED'
                confirm_days += 1
                shrinks[i] = round(vol / vol_s, 4)

                if pct <= self.fail_pct and vol >= self.fail_vol_ratio * vol_s:
                    # 确认后再放量暴跌：形态失败
                    score = 0
                    phase = 'SEARCHING'
                    states[i] = 'EXPIRED'
                    ev = '形态失败'
                elif confirm_days > self.max_pullback_days:
                    # 形态完结归档，回到寻找新信号
                    score = 0
                    phase = 'SEARCHING'
                    states[i] = 'SEARCHING'
                    ev = '形态结束'
                else:
                    states[i] = 'CONFIRMED'
                    if pct >= self.rebound_pct and prev_vol is not None and vol >= prev_vol:
                        # 加速上攻：继续加分
                        score += self._CONTINUE_BONUS
                patterns[i] = score

            events[i] = ev

        out['day_score'] = day_scores
        out['state'] = states
        out['shrink_ratio'] = shrinks
        out['pattern_score'] = patterns
        out['event'] = events

        # 恢复输入原顺序
        if reversed_input:
            out = out.iloc[::-1].reset_index(drop=True)
        return out

    # ---------- 内部方法 ----------

    def _is_signal(self, pct: float, vr5: float) -> bool:
        """
        判断是否为爆量信号日

        条件（满足任一）：
            - vr5 >= vr_signal 且 涨幅 >= pct_signal
            - vr5 >= vr_strong 且 涨幅 >= pct_strong（低位首日启动容忍）
        """
        if pd.isna(vr5):
            return False
        return (vr5 >= self.vr_signal and pct >= self.pct_signal) or \
               (vr5 >= self.vr_strong and pct >= self.pct_strong)

    def _calc_day_score(self, pct: float, vr5: float) -> int:
        """
        计算单日量价分（Layer1）

        组成：涨跌方向分（pct*8，截断±40） + 量价配合分（查表）
        量价配合分核心逻辑：缩量下跌为正分（抛压衰竭），放量大跌为最重负分
        """
        direction = max(-40.0, min(40.0, pct * 8))

        if pd.isna(vr5):
            vol_score = 0
        elif pct > 0:
            if vr5 >= 2.5:
                vol_score = 40      # 爆量上涨
            elif vr5 >= 1.2:
                vol_score = 30      # 温和放量上涨
            elif vr5 < 0.7:
                vol_score = 20      # 缩量上涨（惜售）
            else:
                vol_score = 15      # 常量上涨
        elif pct < 0:
            if vr5 >= 2.0:
                vol_score = -40     # 放量大跌（出货嫌疑）
            elif vr5 >= 1.2:
                vol_score = -25     # 带量下跌
            elif vr5 < 0.5:
                vol_score = 15      # 极度缩量下跌（抛压衰竭，本形态灵魂）
            else:
                vol_score = -5      # 常量下跌
        else:
            vol_score = 0

        return int(round(max(-100.0, min(100.0, direction + vol_score))))

    def _pullback_delta(self, pct: float, shrink: float,
                        depth: float, prev_abs_pct) -> int:
        """
        计算回调蓄势日的四项加减分（Layer2）

        Args:
            pct: 当日涨跌幅(%)
            shrink: 当日量 / 信号日量
            depth: 收盘价相对信号日收盘价的回撤（close/close_s - 1）
            prev_abs_pct: 前一交易日涨跌幅绝对值（无则为None）

        Returns:
            int: 当日加减总分
        """
        delta = 0
        s_strong, s_clear, s_mild = self.shrink_levels

        # ① 缩量分（相对信号日量的收缩比）
        if shrink <= s_strong:
            delta += 10            # 极度缩量，洗盘充分
        elif shrink <= s_clear:
            delta += 7             # 明显缩量
        elif shrink <= s_mild:
            delta += 4             # 温和缩量
        elif shrink > 1.0:
            delta -= 10            # 再爆量（滞涨/出货嫌疑）
        # s_mild ~ 1.0 区间：0分

        # ② 跌幅分（回调期价格行为）
        if -1 <= pct < 0:
            delta += 8             # 小跌，最理想
        elif -3 <= pct < -1:
            delta += 3             # 中跌
        elif -6 <= pct < -3:
            delta -= 5             # 大跌
        elif pct < -6:
            delta -= 15            # 暴跌，破坏形态
        else:
            # 0 <= pct < 3 企稳；pct >= 3 但量能未达确认标准，按企稳处理
            delta += 5

        # ③ 收敛分（跌幅收敛）
        if prev_abs_pct is not None and abs(pct) < prev_abs_pct:
            delta += self._CONVERGE_BONUS

        # ④ 深度分（相对信号日收盘的累计回撤）
        if depth > -0.05:
            delta += 8             # 浅回调，强势
        elif depth > -0.10:
            delta += 3
        elif depth > -0.15:
            delta -= 3
        else:
            delta -= 8             # 回调过深

        return delta

    def _is_descending(self, df: pd.DataFrame) -> bool:
        """判断DataFrame是否按时间倒序排列（最新在前）"""
        if len(df) < 2:
            return False
        for col in ('datetime', 'trade_date'):
            if col in df.columns:
                return df[col].iloc[0] > df[col].iloc[-1]
        return False
