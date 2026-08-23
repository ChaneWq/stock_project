"""
量比策略扫描 Web 服务

启动：
    python -m app.minute_vr_scanner.web
    或直接运行：
    python app/minute_vr_scanner/web.py
访问：
    http://127.0.0.1:5001/

接口：
    GET  /               渲染扫描页面
    GET  /api/init       默认参数（最新交易日、codes.txt 内容）
    POST /api/scan       启动后台扫描，返回 task_id
    GET  /api/status     轮询扫描进度/结果
    GET  /api/detail     单只股票分时量比明细（图表用）
"""

import os
import sys
import threading
import uuid

from flask import Flask, render_template, jsonify, request

# 兼容两种启动方式（惯例同 stock_monitor）
try:
    from .scanner import scan, get_latest_trade_date, get_minute_detail
    from . import config
except ImportError:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from app.minute_vr_scanner.scanner import scan, get_latest_trade_date, get_minute_detail
    from app.minute_vr_scanner import config

app = Flask(__name__)

# 任务状态：内存存储（单用户工具，无需持久化）
_tasks = {}
_tasks_lock = threading.Lock()

# 过滤前缀（同 CLI：创业板/科创板/北交所）
FILTER_PREFIXES = ('300', '301', '688', '9')


def _load_default_codes():
    """读取默认 codes.txt（与模块同目录）"""
    codes_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'codes.txt')
    if not os.path.exists(codes_file):
        return ''
    with open(codes_file, 'r', encoding='utf-8-sig') as f:
        return f.read()


def _run_scan_task(task_id, codes, date, strategy_id, params):
    """后台扫描线程：调用 scan()，progress_callback 更新任务状态"""
    task = _tasks[task_id]
    try:
        def on_progress(done, total):
            task['done'] = done
            task['total'] = total

        results = scan(
            codes, date, strategy_id,
            n=params['n'],
            until_hour=params['until_hour'], until_minute=params['until_minute'],
            change_min=params['change_min'], change_max=params['change_max'],
            progress_callback=on_progress,
            **params['strategy_kwargs'],
        )
        task['results'] = results
        task['status'] = 'done'
    except Exception as e:
        task['status'] = 'error'
        task['error'] = str(e)


@app.route('/')
def index():
    """扫描页面"""
    return render_template('scanner.html')


@app.route('/api/init')
def api_init():
    """默认参数：最新交易日 + codes.txt 内容"""
    codes_text = _load_default_codes()
    codes = [c.strip() for c in codes_text.splitlines() if c.strip()]
    # 过滤板块（同 CLI 逻辑）
    codes = [c for c in codes if not c.startswith(FILTER_PREFIXES)]
    date = get_latest_trade_date(codes)
    return jsonify({'date': date, 'codes': '\n'.join(codes)})


@app.route('/api/scan', methods=['POST'])
def api_scan():
    """启动后台扫描"""
    data = request.get_json(force=True)

    # 解析股票代码
    codes_text = data.get('codes', '')
    codes = [c.strip() for c in codes_text.replace(',', '\n').splitlines() if c.strip()]
    if not codes:
        return jsonify({'error': '股票列表为空'}), 400

    # 板块过滤（可前端关闭）
    if not data.get('no_filter', False):
        codes = [c for c in codes if not c.startswith(FILTER_PREFIXES)]
    if not codes:
        return jsonify({'error': '过滤后股票列表为空'}), 400

    strategy_id = data.get('strategy', 'vr_slope')
    if strategy_id not in ('vr_slope', 'vr_anomaly'):
        return jsonify({'error': f'未知策略: {strategy_id}'}), 400

    # 日期：空则取最新交易日
    date = data.get('date', '') or get_latest_trade_date(codes)

    # 截至时间
    until = data.get('until', '')
    until_hour = until_minute = None
    if until:
        try:
            parts = until.split(':')
            until_hour, until_minute = int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return jsonify({'error': '截至时间格式错误，应为 HH:MM'}), 400

    # 策略参数
    if strategy_id == 'vr_slope':
        strategy_kwargs = {
            'window': int(data.get('vr_slope_window', 3)),
            'vr_slope': float(data.get('vr_slope', 5)),
            'vr_up': not data.get('no_vr_up', False),
            'price_up': not data.get('no_vr_slope_price_up', False),
            'min_hits': int(data.get('vr_slope_min_hits', 3)),
            'merge_gap': int(data.get('vr_slope_merge_gap', 2)),
        }
    else:
        strategy_kwargs = {
            'window': int(data.get('anomaly_window', 3)),
            'steep': float(data.get('anomaly_steep', 5)),
            'turn': float(data.get('anomaly_turn', 8)),
            'price_up': not data.get('no_anomaly_price_up', False),
            'min_hits': int(data.get('anomaly_min_hits', 1)),
            'merge_gap': int(data.get('anomaly_merge_gap', 2)),
        }

    params = {
        'n': int(data.get('n', 5)),
        'until_hour': until_hour,
        'until_minute': until_minute,
        'change_min': float(data.get('change_min', -100)),
        'change_max': float(data.get('change_max', 100)),
        'strategy_kwargs': strategy_kwargs,
    }

    # 创建后台任务
    task_id = uuid.uuid4().hex[:12]
    with _tasks_lock:
        # 简单清理：只保留最近10个任务
        if len(_tasks) >= 10:
            for old_id in list(_tasks.keys())[:-9]:
                _tasks.pop(old_id, None)
        _tasks[task_id] = {
            'status': 'running',
            'done': 0,
            'total': len(codes),
            'results': None,
            'error': None,
            'date': date,
            'strategy': strategy_id,
        }

    t = threading.Thread(target=_run_scan_task, args=(task_id, codes, date, strategy_id, params), daemon=True)
    t.start()

    return jsonify({'task_id': task_id})


@app.route('/api/status')
def api_status():
    """轮询任务进度/结果"""
    task_id = request.args.get('task_id', '')
    with _tasks_lock:
        task = _tasks.get(task_id)
    if task is None:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify({
        'status': task['status'],
        'done': task['done'],
        'total': task['total'],
        'results': task['results'],
        'error': task['error'],
        'date': task['date'],
        'strategy': task['strategy'],
    })


@app.route('/api/detail')
def api_detail():
    """单只股票分时量比明细（图表用）"""
    code = request.args.get('code', '')
    date = request.args.get('date', '')
    n = int(request.args.get('n', 5))
    if not code or not date:
        return jsonify({'error': '缺少 code 或 date 参数'}), 400

    detail = get_minute_detail(code, date, n)
    if detail is None:
        return jsonify({'error': f'未获取到 {code} 在 {date} 的分时数据'}), 404
    return jsonify(detail)


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5001)
