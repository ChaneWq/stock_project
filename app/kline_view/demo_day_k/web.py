"""
日K线可视化 Web 服务（demo）

启动：
    python -m app.kline_view.demo_day_k.web
    或直接运行：
    python app/kline_view/demo_day_k/web.py
访问：
    http://127.0.0.1:5003/

接口：
    GET  /           渲染K线图页面
    GET  /api/kline  查询参数：code + recent（最近N个交易日，默认120）
"""

import os
import sys

import pandas as pd
from flask import Flask, render_template, jsonify, request

# 兼容两种启动方式（惯例同 stock_query）
try:
    from app.data_store import get_daily
except ImportError:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from app.data_store import get_daily

app = Flask(__name__)

MA_WINDOWS = (5, 10, 20, 60)
DEFAULT_RECENT = 120
MAX_RECENT = 800


@app.route('/')
def index():
    """K线图页面"""
    return render_template('index.html')


@app.route('/api/kline')
def api_kline():
    """日K线接口：code + 最近N个交易日（数据走 data_store：本地优先，缺失自动回源）"""
    code = (request.args.get('code') or '').strip()
    if not code:
        return jsonify({'error': '请输入股票代码'}), 400

    recent = (request.args.get('recent') or '').strip()
    try:
        recent = int(recent) if recent else DEFAULT_RECENT
        recent = max(10, min(recent, MAX_RECENT))
    except ValueError:
        return jsonify({'error': '天数须为整数'}), 400

    # 多取 max(MA_WINDOWS)-1 根历史用于均线预热，展示窗口内所有日期才有完整均线值
    buf = max(MA_WINDOWS) - 1

    # 按请求天数换算 start（工作日数+节假日余量），让 data_store 自动深回补
    span = recent + buf
    start = (pd.Timestamp.today() - pd.offsets.BDay(span + max(15, span // 4))).strftime('%Y-%m-%d')

    try:
        df = get_daily(code, start=start)
    except Exception as e:
        return jsonify({'error': f'取数失败：{e}'}), 500

    if df is None or df.empty:
        return jsonify({'error': f'股票 {code} 无日线数据'}), 404

    # data_store 返回最新在前，先取 带 缓冲的最近N根计算均线，再裁剪回展示窗口
    df = df.head(recent + buf).sort_values('trade_date').reset_index(drop=True)

    # 均线（在含缓冲的完整序列上滚动）
    for n in MA_WINDOWS:
        df[f'ma{n}'] = df['close'].rolling(n).mean()

    # 窗口前一根收盘价，作为首日涨跌幅基准
    prev_close = round(float(df['close'].iloc[-recent - 1]), 2) if len(df) > recent else None
    df = df.tail(recent).reset_index(drop=True)

    def ma_list(n):
        return [None if pd.isna(v) else round(float(v), 2) for v in df[f'ma{n}']]

    payload = {
        'code': code,
        'count': len(df),
        'dates': df['trade_date'].astype(str).tolist(),
        # ECharts 蜡烛图数据顺序：[open, close, low, high]
        'candle': df[['open', 'close', 'low', 'high']].round(2).values.tolist(),
        'volumes': [int(v) for v in df['volume']],
        'prev_close': prev_close,
        'ma': {f'ma{n}': ma_list(n) for n in MA_WINDOWS},
    }
    return jsonify(payload)


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5003)
