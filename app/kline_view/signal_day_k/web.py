"""
信号日K线回看 Web 服务

读取 signals.csv（code,trade_date 信号日），将信号日K线醒目标注，
展示信号日前 200 个交易日 ~ 后 20 个交易日的日K线。

启动：
    python -m app.kline_view.signal_day_k.web
访问：
    http://127.0.0.1:5004/

接口：
    GET  /            渲染页面
    GET  /api/signals 信号清单（读 signals.csv，保持文件顺序）
    GET  /api/kline   查询参数：code + date（信号日 YYYY-MM-DD）
"""

import bisect
import os
import sys

import pandas as pd
from flask import Flask, render_template, jsonify, request

# 兼容两种启动方式（惯例同 demo_day_k）
try:
    from app.data_store import get_daily
except ImportError:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from app.data_store import get_daily

app = Flask(__name__)

MA_WINDOWS = (5, 10, 20, 60)
BEFORE = 200   # 信号日前展示的交易日数
AFTER = 20     # 信号日后展示的交易日数

_SIGNALS_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'signals.csv')


def load_signals():
    """读信号清单（保持文件顺序，去除空行与重复行）"""
    if not os.path.exists(_SIGNALS_CSV):
        return []
    df = pd.read_csv(_SIGNALS_CSV, dtype=str, encoding='utf-8-sig')
    df.columns = [c.strip().lower() for c in df.columns]
    if not {'code', 'trade_date'} <= set(df.columns):
        raise ValueError('signals.csv 须包含 code,trade_date 两列')
    df = df[['code', 'trade_date']].dropna()
    df['code'] = df['code'].str.strip()
    df['trade_date'] = df['trade_date'].str.strip()
    df = df[(df['code'] != '') & (df['trade_date'] != '')].drop_duplicates()
    return df.to_dict('records')


@app.route('/')
def index():
    """K线图页面"""
    return render_template('index.html')


@app.route('/api/signals')
def api_signals():
    """信号清单接口"""
    try:
        return jsonify(load_signals())
    except Exception as e:
        return jsonify({'error': f'读取 signals.csv 失败：{e}'}), 500


@app.route('/api/kline')
def api_kline():
    """信号日窗口K线接口：信号日前200 ~ 后20个交易日（数据走 data_store）"""
    code = (request.args.get('code') or '').strip()
    signal_date = (request.args.get('date') or '').strip()
    if not code:
        return jsonify({'error': '请输入股票代码'}), 400

    try:
        sdt = pd.Timestamp(signal_date)
        if sdt is pd.NaT:
            raise ValueError
        signal_date = sdt.strftime('%Y-%m-%d')
    except Exception:
        return jsonify({'error': '信号日期格式须为 YYYY-MM-DD'}), 400

    # 多取 max(MA_WINDOWS)-1 根历史用于均线预热，展示窗口内所有日期才有完整均线值
    buf = max(MA_WINDOWS) - 1

    # 按交易日数换算 start/end（工作日数+节假日余量），让 data_store 自动回补
    span = BEFORE + buf
    start = (sdt - pd.offsets.BDay(span + max(15, span // 4))).strftime('%Y-%m-%d')
    end = (sdt + pd.offsets.BDay(AFTER + max(15, AFTER // 4))).strftime('%Y-%m-%d')

    try:
        df = get_daily(code, start=start, end=end)
    except Exception as e:
        return jsonify({'error': f'取数失败：{e}'}), 500

    if df is None or df.empty:
        return jsonify({'error': f'股票 {code} 在 {start}~{end} 无日线数据'}), 404

    df = df.sort_values('trade_date').reset_index(drop=True)
    dates = df['trade_date'].astype(str).tolist()

    # 定位信号日：非交易日自动前移到最近一个交易日；晚于最新数据则标注至最新
    note = None
    pos = bisect.bisect_left(dates, signal_date)
    if pos >= len(dates):
        idx = len(dates) - 1
        note = f'信号日 {signal_date} 晚于最新数据 {dates[idx]}，已标注至最新交易日'
    elif dates[pos] != signal_date:
        if pos == 0:
            return jsonify({'error': f'信号日 {signal_date} 早于数据起点 {dates[0]}（股票上市晚于信号日？）'}), 404
        idx = pos - 1
        note = f'信号日 {signal_date} 为非交易日，已标注至前一交易日 {dates[idx]}'
    else:
        idx = pos

    # 预热窗口上算均线，再裁剪回展示窗口 [idx-200, idx+20]
    warm_lo = max(0, idx - BEFORE - buf)
    warm = df.iloc[warm_lo: idx + AFTER + 1].copy()
    for n in MA_WINDOWS:
        warm[f'ma{n}'] = warm['close'].rolling(n).mean()

    # 展示窗口前一根收盘价，作为首日涨跌幅基准
    prev_i = idx - BEFORE - 1
    prev_close = round(float(df['close'].iloc[prev_i]), 2) if prev_i >= 0 else None

    show_lo = max(0, idx - BEFORE)
    win = warm.iloc[show_lo - warm_lo:].reset_index(drop=True)

    def ma_list(n):
        return [None if pd.isna(v) else round(float(v), 2) for v in win[f'ma{n}']]

    # 同 code 其它信号日落在展示窗口内的索引（前端弱标注）
    other_idx = []
    try:
        for s in load_signals():
            if s['code'] == code and s['trade_date'] != dates[idx]:
                p = bisect.bisect_left(dates, s['trade_date'])
                if p < len(dates) and dates[p] == s['trade_date'] and show_lo <= p <= idx + AFTER:
                    other_idx.append(p - show_lo)
    except Exception:
        pass

    # 信号日后交易日不足 AFTER 个时提示
    after_cnt = min(AFTER, len(dates) - 1 - idx)
    if after_cnt < AFTER:
        note = (note + '；' if note else '') + f'信号日后仅 {after_cnt} 个交易日'

    payload = {
        'code': code,
        'signal_date': dates[idx],
        'signal_index': idx - show_lo,
        'other_signals': other_idx,
        'count': len(win),
        'dates': win['trade_date'].astype(str).tolist(),
        # ECharts 蜡烛图数据顺序：[open, close, low, high]
        'candle': win[['open', 'close', 'low', 'high']].round(2).values.tolist(),
        'volumes': [int(v) for v in win['volume']],
        'prev_close': prev_close,
        'ma': {f'ma{n}': ma_list(n) for n in MA_WINDOWS},
        'note': note,
    }
    return jsonify(payload)


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5004)
