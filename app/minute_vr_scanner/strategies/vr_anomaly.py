# strategies/vr_anomaly.py - 量比异动策略（显性+隐性）
import math
import numpy as np


def evaluate(df, window=3, steep=5, turn=8, price_up=True, min_hits=1, merge_gap=2):
    """
    量比异动策略：捕捉显性异动（量比急升）和隐性异动（量比拐点反转）

    滑动窗口设计:
        对每个位置 i，取两个相邻窗口：
          前窗: [i, i+window-1]
          后窗: [i+window, i+2*window-1]

    判断逻辑:
        ① 显性异动：后窗量比角度 ≥ steep → 量比急升
        ② 隐性异动：前窗角度 < 0 且 后窗角度 > 0 且 角度差 ≥ turn → 拐点反转
        ③ 价格不跌：后窗 price[end] >= price[start]（price_up=True时）
        任一异动类型命中 → 记录

    参数:
        df: 分时数据 DataFrame，必须包含 price, volume_ratio, time_index, hour, minute 列
        window: 每段窗口大小（分钟），默认3
        steep: 显性异动角度阈值（度），默认5
        turn: 隐性异动角度差阈值（度），默认8
        price_up: 是否要求后窗首尾价格不下跌，默认True
        min_hits: 最少命中次数，默认1
        merge_gap: 命中间隔 ≤ 此值合并为同一时段，默认2

    返回:
        dict: 策略评分结果，不满足条件返回 None
    """
    if df is None or len(df) < 2 * window:
        return None

    price = df['price'].values
    volume_ratio = df['volume_ratio'].values
    hour = df['hour'].values.astype(int)
    minute = df['minute'].values.astype(int)

    # 全天价格斜率（归一化）
    time_index = df['time_index'].values
    price_slope = _slope(time_index, price) / np.mean(price)

    # 滑动扫描
    total_positions = len(df) - 2 * window + 1
    hit_count = 0
    hit_indices = []  # 记录后窗起始位置
    hit_types = []    # 'steep' 或 'turn'
    hit_angles = []   # 显性: 后窗角度; 隐性: 角度差

    for i in range(total_positions):
        # 前窗 [i, i+window-1]
        front_end = i + window - 1
        vr_front_start = volume_ratio[i]
        vr_front_end = volume_ratio[front_end]
        front_slope = (vr_front_end - vr_front_start) / (window - 1)
        front_angle = math.degrees(math.atan(front_slope))

        # 后窗 [i+window, i+2*window-1]
        back_start = i + window
        back_end = i + 2 * window - 1
        vr_back_start = volume_ratio[back_start]
        vr_back_end = volume_ratio[back_end]
        back_slope = (vr_back_end - vr_back_start) / (window - 1)
        back_angle = math.degrees(math.atan(back_slope))

        # 价格不跌（后窗首尾）
        if price_up and price[back_end] < price[back_start]:
            continue

        is_steep = back_angle >= steep
        is_turn = (front_angle < 0 and back_angle > 0 and
                   (back_angle - front_angle) >= turn)

        if is_steep or is_turn:
            hit_count += 1
            hit_indices.append(i)
            if is_steep and is_turn:
                hit_types.append('both')
                hit_angles.append(max(back_angle, back_angle - front_angle))
            elif is_steep:
                hit_types.append('steep')
                hit_angles.append(back_angle)
            else:
                hit_types.append('turn')
                hit_angles.append(back_angle - front_angle)

    if hit_count < min_hits:
        return None

    # 统计
    steep_count = sum(1 for t in hit_types if t in ('steep', 'both'))
    turn_count = sum(1 for t in hit_types if t in ('turn', 'both'))
    max_angle_diff = max(hit_angles)

    # 合并连续命中为时段
    hit_periods = _merge_indices_to_periods(hit_indices, window, hour, minute, merge_gap)

    # 综合评分
    score = max_angle_diff * hit_count * (1 + price_slope)

    return {
        'score': round(score, 4),
        'steep_hits': steep_count,
        'turn_hits': turn_count,
        'max_angle_diff': round(max_angle_diff, 1),
        'hit_windows': hit_count,
        'total_windows': total_positions,
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
    """将命中的位置索引合并为时段"""
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

    periods = []
    for s, e in groups:
        # 时段从前窗开头到后窗末尾
        start_time = "%02d:%02d" % (hour[s], minute[s])
        end_idx = e + 2 * window - 1
        end_time = "%02d:%02d" % (hour[end_idx], minute[end_idx])
        periods.append("%s-%s" % (start_time, end_time))

    return ", ".join(periods)
