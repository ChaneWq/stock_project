"""
个股监控 Flask 服务

启动：
    python -m app.stock_monitor.server
    或直接运行：
    python app/stock_monitor/server.py
访问：
    http://127.0.0.1:5000/
"""

import os
import re
import sys
from flask import Flask, render_template, jsonify, request

# 兼容两种启动方式：
#   1) python -m app.stock_monitor.server   （相对导入可用）
#   2) python app/stock_monitor/server.py    （相对导入不可用，回退绝对导入）
try:
    from .stocks import load_stocks
    from .monitor import collect_all
except ImportError:
    # 把项目根目录加入 sys.path，使 app.stock_monitor.* 可被导入
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from app.stock_monitor.stocks import load_stocks
    from app.stock_monitor.monitor import collect_all

app = Flask(__name__)

# 合法日期：8位数字（YYYYMMDD）
_DATE_RE = re.compile(r'^\d{8}$')


def _parse_query_date(raw):
    """
    解析查询日期参数

    支持 YYYY-MM-DD / YYYYMMDD 两种格式；
    非法或缺省返回 None（表示当日实时）。
    """
    if not raw:
        return None
    s = raw.strip().replace('-', '')
    return s if _DATE_RE.match(s) else None


@app.route('/')
def index():
    """首页：采集数据并渲染表格（支持 ?date=YYYY-MM-DD 查询历史日期）"""
    date = _parse_query_date(request.args.get('date'))
    data = collect_all(load_stocks(), date)
    return render_template('index.html', data=data, query_date=date)


@app.route('/api/data')
def api_data():
    """数据接口：前端刷新按钮调用（支持 ?date=YYYY-MM-DD 查询历史日期）"""
    date = _parse_query_date(request.args.get('date'))
    data = collect_all(load_stocks(), date)
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
