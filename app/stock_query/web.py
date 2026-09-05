"""
个股数据展示 Web 服务

启动：
    python -m app.stock_query.web
    或直接运行：
    python app/stock_query/web.py
访问：
    http://127.0.0.1:5002/

接口：
    GET  /            渲染查询页面
    GET  /api/query   查询参数：code + (start,end) 或 recent_days
"""

import os
import sys

from flask import Flask, render_template, jsonify, request

# 兼容两种启动方式（惯例同 stock_monitor）
try:
    from .query import query_stock, query_minutes
except ImportError:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from app.stock_query.query import query_stock, query_minutes

app = Flask(__name__)


@app.route('/')
def index():
    """查询页"""
    return render_template('index.html')


@app.route('/api/query')
def api_query():
    """数据接口：code + 日期区间 或 最近N天"""
    code = (request.args.get('code') or '').strip()
    if not code:
        return jsonify({'error': '请输入股票代码'}), 400

    start = (request.args.get('start') or '').strip()
    end = (request.args.get('end') or '').strip()
    recent = (request.args.get('recent') or '').strip()

    try:
        if recent:
            data = query_stock(code, recent_days=int(recent))
        elif start or end:
            data = query_stock(code, start_date=start or None, end_date=end or None)
        else:
            data = query_stock(code, recent_days=30)  # 默认最近30个交易日
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'查询失败：{e}'}), 500

    if not data:
        return jsonify({'error': f'股票 {code} 在该范围内无数据'}), 404
    return jsonify({'code': code, 'count': len(data), 'data': data})


@app.route('/api/minutes')
def api_minutes():
    """分时接口：某交易日的全天分时数据（240行正序）"""
    code = (request.args.get('code') or '').strip()
    date = (request.args.get('date') or '').strip()
    if not code:
        return jsonify({'error': '请输入股票代码'}), 400
    if not date:
        return jsonify({'error': '请选择日期'}), 400

    try:
        data = query_minutes(code, date)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'查询失败：{e}'}), 500

    if not data:
        return jsonify({'error': f'股票 {code} 在 {date} 无分时数据'}), 404
    return jsonify({'code': code, 'date': date, 'count': len(data), 'data': data})


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5002)
