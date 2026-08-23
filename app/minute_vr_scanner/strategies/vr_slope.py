# strategies/vr_slope.py - 量比斜率策略
import math
import numpy as np


def evaluate(df, window=3, vr_slope=5, vr_up=True, price_up=True, min_hits=3, merge_gap=2):
    """
    量比斜率策略：滑动窗口扫描量比斜率+价格上涨的时段

    判断逻辑:
        滑动窗口逐段扫描:
          ① 量比斜率角度 ≥ vr_slope → 量比上升够陡
          ② VR[end] > VR[start] → 量比确实增加（vr_up=True时）
          ③ price[end] >= price[start] → 窗口内价格不下跌（price_up=True时）
          三者同时满足 → 命中一个窗口

        合并连续命中窗口为时段（间隔 ≤ merge_gap）
        全天命中窗口数 ≥ min_hits 才算命中

    评分:
        量比平均斜率角度 = sum(命中窗口的量比斜率角度) / 命中窗口数
        综合评分 = 量比平均斜率角度 × 命中窗口数 × 价格斜率(归一化)

    参数:
        df: 分时数据 DataFrame，必须包含 price, volume_ratio, time_index, hour, minute 列
        window: 窗口大小（分钟），默认3
        vr_slope: 量比斜率角度阈值（度），默认5度
        vr_up: 是否要求窗口首尾量比增加，默认True
        price_up: 是否要求窗口首尾价格不下跌，默认True
        min_hits: 最少命中窗口数，默认3
        merge_gap: 命中窗口间隔 ≤ 此值合并为同一时段，默认2

    返回:
        dict: 策略评分结果，不满足条件返回 None
        {
            'score': float,              # 综合评分
            'avg_vr_slope_deg': float,   # 量比平均斜率角度（度）
            'hit_windows': int,          # 命中窗口数
            'total_windows': int,        # 总窗口数
            'price_slope': float,        # 全天价格斜率(归一化)
            'hit_periods': str           # 命中时段
        }
    """
    if df is None or len(df) < window + 1:
        return None

    price = df['price'].values
    volume_ratio = df['volume_ratio'].values
    time_index = df['time_index'].values
    hour = df['hour'].values.astype(int)
    minute = df['minute'].values.astype(int)

    # 全天价格斜率（归一化）
    price_slope = _slope(time_index, price) / np.mean(price)

    # 将角度阈值转为斜率阈值
    slope_threshold = math.tan(math.radians(vr_slope))

    # 滑动窗口扫描
    total_windows = len(df) - window
    hit_count = 0
    hit_indices = []
    hit_slopes_deg = []

    for i in range(total_windows):
        end = i + window - 1

        # ① 量比斜率 = (VR[end] - VR[start]) / window
        vr_start = volume_ratio[i]
        vr_end = volume_ratio[end]
        slope = (vr_end - vr_start) / (window - 1)

        if slope < slope_threshold:
            continue

        # ② 量比增加（窗口首尾比较）
        if vr_up and vr_end <= vr_start:
            continue

        # ③ 价格不下跌（窗口首尾比较）
        if price_up and price[end] < price[i]:
            continue

        hit_count += 1
        hit_indices.append(i)
        hit_slopes_deg.append(math.degrees(math.atan(slope)))

    if hit_count < min_hits:
        return None

    # 合并连续命中窗口为时段
    hit_periods = _merge_indices_to_periods(hit_indices, window, hour, minute, merge_gap)

    # 量比平均斜率角度
    avg_vr_slope_deg = np.mean(hit_slopes_deg)

    # 综合评分
    score = avg_vr_slope_deg * hit_count * price_slope

    return {
        'score': round(score, 4),
        'avg_vr_slope_deg': round(avg_vr_slope_deg, 1),
        'hit_windows': hit_count,
        'total_windows': total_windows,
        'price_slope': round(price_slope, 6),
        'hit_periods': hit_periods,
    }


def _slope(x, y):
    """线性回归斜率"""
    x = np.array(x, dtype=float)
    y = np.array(y, dtype=float)
    n = len(x)
    sum_x = np.sum(x)
    sum_y = np.sum(y)
    sum_xy = np.sum(x * y)
    sum_x2 = np.sum(x * x)
    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denom


def _merge_indices_to_periods(hit_indices, window, hour, minute, merge_gap=2):
    """
    将命中的窗口索引合并为时段

    间隔 ≤ merge_gap 的视为同一时段合并
    """
    if not hit_indices:
        return ""

    groups = []
    start = hit_indices[0]
    end = hit_indices[0]
    for idx in hit_indices[1:]:
        if idx - end <= merge_gap:
            end = idx
        else:
            groups.append((start, end))
            start = idx
            end = idx
    groups.append((start, end))

    # 转为时间字符串
    periods = []
    for s, e in groups:
        start_time = "%02d:%02d" % (hour[s], minute[s])
        end_idx = e + window - 1
        end_time = "%02d:%02d" % (hour[end_idx], minute[end_idx])
        periods.append("%s-%s" % (start_time, end_time))

    return ", ".join(periods)
