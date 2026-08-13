"""
带量比的分时数据模块

功能：
- 获取带量比的分时数据（自动计算量比）
- 需要过去n日日线数据作为基准
- 提供完整的量比分析功能

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import pandas as pd
import numpy as np
from ..source import TdxSource


class BasicMinutesWithVR:
    """
    带量比的分时数据类
    
    功能：
        - 自动获取过去n日日线数据
        - 计算量比并添加到分时数据
        - 提供完整的量比分析功能
    
    使用示例：
        >>> minutes_vr = BasicMinutesWithVR()
        >>> vr_df = minutes_vr.get_data('000400', '20260624', n=5)
        >>> # 包含字段：volume_ratio, cumulative_vol, time_index
    
    参数说明：
        market: 通达信市场参数，默认为'std'
    
    量比说明：
        - 量比 = 当日分钟均量 / 过去n日分钟均量
        - 量比 > 3: 明显放量
        - 量比 2~3: 放量
        - 量比 1~2: 正常
        - 量比 0.5~1: 缩量
        - 量比 < 0.5: 明显缩量
    
    Note:
        - 需要过去n日日线数据计算量比
        - 数据量比BasicMinutes多，性能稍慢
        - 适用于分时量比分析场景
    """
    
    def __init__(self, market: str = 'std', thread_safe: bool = False):
        """
        初始化带量比的分时数据类

        Args:
            market (str): 通达信市场参数，默认为'std'
            thread_safe (bool): 是否使用线程独立 client，默认 False
                多线程并发采集时设为 True，每个线程拥有独立 client
        """
        self.source = TdxSource(market=market, thread_safe=thread_safe)
        self._avg_vol_per_minute = None  # 缓存分钟均量
        self._prev_n_day_vol_list = None  # 缓存过去n日成交量列表
        self._prev_close = None  # 缓存昨收价
    
    def get_data(self, code: str, date: str, n: int = 5) -> pd.DataFrame:
        """
        获取带量比的分时数据
        
        Args:
            code (str): 股票代码（6位字符串）
            date (str): 日期（格式YYYYMMDD）
            n (int): 过去n个交易日，默认5
        
        Returns:
            DataFrame: 带量比的分时数据
        
        Raises:
            ValueError: 如果缺少必需字段
        
        Example:
            >>> minutes_vr = BasicMinutesWithVR()
            >>> vr_df = minutes_vr.get_data('000400', '20260624', n=5)
            >>> # 返回240行分时数据（包含量比）
        
        Note:
            - 自动获取过去n日日线数据
            - 计算量比并添加到分时数据
            - 数据量比BasicMinutes多
        """
        # Step 1: 获取当日分时数据
        minute_df = self.source.fetch_minutes(code, date)
        
        if minute_df.empty:
            print(f"[BasicMinutesWithVR] 未获取到 {code} 在 {date} 的分时数据")
            return pd.DataFrame()
        
        # Step 2: 获取过去n日日线成交量
        day_data = self.source.fetch_prev_n_day_vol(code, n, date)
        
        if not day_data:
            print(f"[BasicMinutesWithVR] 未获取到 {code} 过去{n}日日线数据")
            return pd.DataFrame()
        
        vol_list = day_data['vol_list']
        self._prev_close = day_data['prev_close']
        
        # Step 3: 计算过去n日每分钟平均成交量
        self._avg_vol_per_minute = self._calc_avg_vol_per_minute(vol_list, n)
        self._prev_n_day_vol_list = vol_list
        
        # Step 4: 计算量比并添加到DataFrame
        vr_df = self._calc_volume_ratio(minute_df, self._avg_vol_per_minute)
        
        return vr_df
    
    def _calc_avg_vol_per_minute(self, day_vol_list: list, n: int) -> float:
        """
        计算过去n日每分钟平均成交量
        
        公式: sum(过去n日成交量) / (n * 240)
        
        Args:
            day_vol_list (list): 过去n个交易日的成交量列表
            n (int): 交易日天数
        
        Returns:
            float: 每分钟平均成交量
        
        Note:
            - 每日有240分钟交易时间
            - 分钟均量用于量比计算基准
        """
        total_vol = sum(day_vol_list[-n:])
        return total_vol / (n * 240)
    
    def _calc_time_index(self, hour, minute) -> np.ndarray:
        """
        计算时间序号（通达信公式）
        
        公式: 时间序号:=IF(HOUR>12,(HOUR-13)*60+MINUTE+120,(HOUR-9)*60+MINUTE-30)+1
        
        Args:
            hour: 小时（int或array）
            minute: 分钟（int或array）
        
        Returns:
            ndarray: 时间序号（1~240）
        
        验证:
            9:30  → (9-9)*60+30-30+1 = 1
            11:29 → (11-9)*60+29-30+1 = 120
            13:00 → (13-13)*60+0+120+1 = 121
            14:59 → (14-13)*60+59+120+1 = 240
        """
        hour = np.array(hour)
        minute = np.array(minute)
        
        # 向量化计算
        morning = (hour - 9) * 60 + minute - 30
        afternoon = (hour - 13) * 60 + minute + 120
        result = np.where(hour > 12, afternoon, morning) + 1
        
        return result
    
    def _calc_volume_ratio(self, minute_df: pd.DataFrame, avg_vol_per_minute: float) -> pd.DataFrame:
        """
        计算量比
        
        公式: 量比 = 当日累计成交量 / 时间序号 / 过去n日分钟均量
        
        Args:
            minute_df (DataFrame): 分时数据，必须包含volume, hour, minute字段
            avg_vol_per_minute (float): 过去n日每分钟平均成交量
        
        Returns:
            DataFrame: 增强数据（新增volume_ratio, cumulative_vol, time_index字段）
        
        Note:
            - 累计成交量：从开盘开始的累计值
            - 时间序号：1~240（9:30~14:59）
            - 量比反映当日成交量相对历史平均的程度
        """
        df = minute_df.copy()
        
        # 处理重复的volume字段（如果存在）
        if isinstance(df['volume'], pd.DataFrame):
            volume_series = df['volume'].iloc[:, 0]
        else:
            volume_series = df['volume']
        
        # 计算时间序号
        df['time_index'] = self._calc_time_index(df['hour'].values, df['minute'].values)
        
        # 计算累计成交量
        df['cumulative_vol'] = volume_series.cumsum()
        
        # 计算量比 = 累计成交量 / 时间序号 / 过去n日分钟均量
        df['volume_ratio'] = df['cumulative_vol'] / df['time_index'] / avg_vol_per_minute
        
        # 保留两位小数
        df['volume_ratio'] = df['volume_ratio'].round(2)
        
        # 添加分钟均量字段（方便用户查看）
        df['avg_vol_per_minute'] = avg_vol_per_minute
        
        return df
    
    def get_avg_vol_per_minute(self) -> float:
        """
        获取过去n日每分钟平均成交量
        
        Returns:
            float: 过去n日每分钟平均成交量
        
        Note:
            - 需先调用get_data()方法
            - 用于量比计算基准
        """
        return self._avg_vol_per_minute
    
    def get_prev_n_day_vol_list(self) -> list:
        """
        获取过去n日成交量列表
        
        Returns:
            list: 过去n个交易日的成交量列表
        
        Note:
            - 需先调用get_data()方法
            - 用于量比计算
        """
        return self._prev_n_day_vol_list
    
    def get_prev_close(self) -> float:
        """
        获取昨收价
        
        Returns:
            float: 目标日期前一交易日收盘价
        
        Note:
            - 需先调用get_data()方法
            - 用于分时涨幅计算等
        """
        return self._prev_close
    
    def get_volume_ratio_summary(self, vr_df: pd.DataFrame) -> dict:
        """
        获取量比统计摘要
        
        Args:
            vr_df (DataFrame): 带量比的分时数据
        
        Returns:
            dict: {'max': 最大量比, 'min': 最小量比, 'avg': 平均量比, 'current': 当前量比}
        
        Example:
            >>> summary = minutes_vr.get_volume_ratio_summary(vr_df)
            >>> print(f"最大量比: {summary['max']}")
        """
        if vr_df.empty:
            return None
        
        vr = vr_df['volume_ratio']
        return {
            'max': float(vr.max()),
            'min': float(vr.min()),
            'avg': float(vr.mean()),
            'current': float(vr.iloc[-1])
        }
    
    def get_volume_ratio_trend(self, vr_df: pd.DataFrame, window: int = 10) -> str:
        """
        判断量比趋势
        
        Args:
            vr_df (DataFrame): 带量比的分时数据
            window (int): 判断窗口大小（分钟），默认10
        
        Returns:
            str: '上升' / '下降' / '平稳' / '数据不足'
        
        Example:
            >>> trend = minutes_vr.get_volume_ratio_trend(vr_df, window=10)
            >>> print(f"量比趋势: {trend}")
        """
        if len(vr_df) < window:
            return '数据不足'
        
        recent = vr_df['volume_ratio'].tail(window)
        slope = (recent.iloc[-1] - recent.iloc[0]) / (window - 1)
        
        if slope > 0.05:
            return '上升'
        elif slope < -0.05:
            return '下降'
        else:
            return '平稳'
    
    def filter_volume_ratio_by_range(self, vr_df: pd.DataFrame, min_vr: float = None, max_vr: float = None) -> pd.DataFrame:
        """
        按量比范围过滤时段
        
        Args:
            vr_df (DataFrame): 带量比的分时数据
            min_vr (float): 量比下限，None表示不限
            max_vr (float): 量比上限，None表示不限
        
        Returns:
            DataFrame: 符合条件的时段
        
        Example:
            >>> high_vr_df = minutes_vr.filter_volume_ratio_by_range(vr_df, min_vr=2.0)
            >>> print(f"量比>=2.0的分钟数: {len(high_vr_df)}")
        """
        mask = True
        if min_vr is not None:
            mask = mask & (vr_df['volume_ratio'] >= min_vr)
        if max_vr is not None:
            mask = mask & (vr_df['volume_ratio'] <= max_vr)
        
        return vr_df[mask].reset_index(drop=True)
    
    def find_volume_ratio_peaks(self, vr_df: pd.DataFrame, threshold: float = 3.0) -> list:
        """
        查找量比峰值时段
        
        Args:
            vr_df (DataFrame): 带量比的分时数据
            threshold (float): 量比阈值，默认3.0
        
        Returns:
            list: [(时间, 量比), ...] 按量比降序排列
        
        Example:
            >>> peaks = minutes_vr.find_volume_ratio_peaks(vr_df, threshold=3.0)
            >>> for time_str, vr_value in peaks:
            >>>     print(f"{time_str}: {vr_value}")
        """
        high_vr = self.filter_volume_ratio_by_range(vr_df, min_vr=threshold)
        
        if high_vr.empty:
            return []
        
        peaks = []
        for _, row in high_vr.iterrows():
            time_str = f"{int(row['hour']):02d}:{int(row['minute']):02d}"
            peaks.append((time_str, float(row['volume_ratio'])))
        
        # 按量比降序排列
        peaks.sort(key=lambda x: x[1], reverse=True)
        return peaks