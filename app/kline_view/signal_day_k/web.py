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
    GET  /api/groups  分组/标记/书签清单
    POST /api/groups  创建分组（JSON: name）
    DELETE /api/groups 删除分组（JSON: name，同时清理该组全部标记与书签）
    POST /api/tags    标记信号归属分组（JSON: code, date, groups[]，整体替换；
                      信号被移出分组时级联清除指向该信号的分组书签）
    POST /api/bookmark  标记分组书签（JSON: group, code, date；书签只前进不后退）
    DELETE /api/bookmark 取消分组书签（JSON: group）
"""

import bisect
import json
import os
import sys

import pandas as pd
from flask import Flask, render_template, jsonify, request

# 兼容两种启动方式（惯例同 demo_day_k）
try:
    from app.data_store import get_daily
    from pystock_data.indicators import (
        MAIndicator, ZXShortTermTrendIndicator, ZXBullBearLineIndicator, MABiasIndicator)
except ImportError:
    _PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if _PROJECT_ROOT not in sys.path:
        sys.path.insert(0, _PROJECT_ROOT)
    from app.data_store import get_daily
    from pystock_data.indicators import (
        MAIndicator, ZXShortTermTrendIndicator, ZXBullBearLineIndicator, MABiasIndicator)

app = Flask(__name__)

MA_PERIOD = 7      # 展示均线
ZX_WARMUP = 120    # 预热根数：牛熊分界最长均线 m4=114（前113行为NaN），EMA双层平滑精度建议≥120
BEFORE = 200       # 信号日前展示的交易日数
AFTER = 20         # 信号日后展示的交易日数

# 展示指标键（payload.ma 与前端约定一致；vol_pct/ma7_slope/bias7 为派生指标，仅面板显示值不画线）
IND_KEYS = ('ma7', 'zx_short_term_trend', 'zx_bull_bear_line', 'vol_pct', 'ma7_slope', 'bias7')

# 指标实例创建一次复用（工程惯例，避免每请求重复实例化）
_ma_ind = MAIndicator(periods=[MA_PERIOD])
_zx_trend_ind = ZXShortTermTrendIndicator()
_zx_bullbear_ind = ZXBullBearLineIndicator()
_mabias_ind = MABiasIndicator()  # 默认 periods=[7] → bias7

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


# 分组与标记持久化文件（本地配置，不入 git）；"全部"为内置虚拟分组不落文件
_GROUPS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'groups.json')


def load_groups():
    """读分组/标记/书签（文件缺失/损坏回退空结构，不报错）"""
    if not os.path.exists(_GROUPS_JSON):
        return {'groups': [], 'tags': {}, 'bookmarks': {}}
    try:
        with open(_GROUPS_JSON, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError('groups.json 结构异常')
        groups = [str(g) for g in data.get('groups', [])]
        tags = {str(k): [str(g) for g in v if g in groups]
                for k, v in data.get('tags', {}).items() if isinstance(v, list)}
        # 书签：{分组名: "code|date"}，分组须存在（"全部"为内置键）；旧文件无此字段视为空
        bookmarks = {}
        raw_bm = data.get('bookmarks', {})
        if isinstance(raw_bm, dict):
            for k, v in raw_bm.items():
                k, v = str(k), str(v)
                if (k in groups or k == '全部') and '|' in v:
                    bookmarks[k] = v
        return {'groups': groups, 'tags': {k: v for k, v in tags.items() if v}, 'bookmarks': bookmarks}
    except Exception:
        return {'groups': [], 'tags': {}, 'bookmarks': {}}


def save_groups(data):
    """落盘（先写临时文件再替换，避免写一半损坏）"""
    tmp = _GROUPS_JSON + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _GROUPS_JSON)


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


@app.route('/api/groups', methods=['GET', 'POST', 'DELETE'])
def api_groups():
    """分组管理：GET 清单 / POST 创建 / DELETE 删除（连带清理标记）"""
    if request.method == 'GET':
        return jsonify(load_groups())

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': '分组名不能为空'}), 400
    if name == '全部':
        return jsonify({'error': '"全部"为内置分组，不能创建或删除'}), 400

    g = load_groups()
    if request.method == 'POST':
        if name in g['groups']:
            return jsonify({'error': f'分组「{name}」已存在'}), 400
        g['groups'].append(name)
        save_groups(g)
        return jsonify({'ok': True})

    # DELETE：删除分组并清理所有信号上该组标记与该书签
    if name not in g['groups']:
        return jsonify({'error': f'分组「{name}」不存在'}), 404
    g['groups'].remove(name)
    g['tags'] = {k: [t for t in v if t != name] for k, v in g['tags'].items()}
    g['tags'] = {k: v for k, v in g['tags'].items() if v}
    g['bookmarks'].pop(name, None)
    save_groups(g)
    return jsonify({'ok': True})


@app.route('/api/tags', methods=['POST'])
def api_tags():
    """标记信号（code+date）归属分组（groups 列表整体替换，空列表=取消全部标记）"""
    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    date = (data.get('date') or '').strip()
    groups = data.get('groups')
    if not code or not date:
        return jsonify({'error': '缺少 code/date 参数'}), 400
    if not isinstance(groups, list):
        return jsonify({'error': 'groups 须为数组'}), 400

    g = load_groups()
    unknown = [x for x in groups if x not in g['groups']]
    if unknown:
        return jsonify({'error': f'分组不存在：{",".join(unknown)}'}), 400

    key = f'{code}|{date}'
    if groups:
        g['tags'][key] = groups
    else:
        g['tags'].pop(key, None)
    # 信号被移出分组时，级联清除指向该信号的书签（"全部"书签不受标记影响）
    for grp in list(g['bookmarks']):
        if grp != '全部' and g['bookmarks'][grp] == key and grp not in g['tags'].get(key, []):
            del g['bookmarks'][grp]
    save_groups(g)
    return jsonify({'ok': True})


@app.route('/api/bookmark', methods=['POST', 'DELETE'])
def api_bookmark():
    """分组书签：POST 标记（书签只前进，新位置更前时保留原书签）/ DELETE 取消"""
    data = request.get_json(silent=True) or {}
    group = (data.get('group') or '').strip()
    if not group:
        return jsonify({'error': '缺少 group 参数'}), 400

    g = load_groups()
    if group != '全部' and group not in g['groups']:
        return jsonify({'error': f'分组「{group}」不存在'}), 404

    if request.method == 'DELETE':
        g['bookmarks'].pop(group, None)
        save_groups(g)
        return jsonify({'ok': True})

    code = (data.get('code') or '').strip()
    date = (data.get('date') or '').strip()
    key = f'{code}|{date}'

    # 用 signals.csv 清单顺序做位置比较（书签=阅读进度，只前进不后退）
    try:
        keys = [f"{s['code']}|{s['trade_date']}" for s in load_signals()]
    except Exception as e:
        return jsonify({'error': f'读取 signals.csv 失败：{e}'}), 500
    if key not in keys:
        return jsonify({'error': f'信号 {key} 不在 signals.csv 中'}), 404

    old = g['bookmarks'].get(group)
    if old and old in keys and keys.index(old) > keys.index(key):
        return jsonify({'ok': True, 'kept': True, 'key': old})   # 保留更靠后的原书签
    g['bookmarks'][group] = key
    save_groups(g)
    return jsonify({'ok': True, 'kept': False, 'key': key})


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

    # 多取预热根数用于指标计算（ZX牛熊分界/EMA精度），展示窗口内所有日期才有完整指标值
    buf = ZX_WARMUP

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
            return jsonify({'error': f'信号日 {signal_date} 早于该股最早交易日 {dates[0]}（股票上市/复牌晚于信号日，无该日K线）'}), 404
        idx = pos - 1
        note = f'信号日 {signal_date} 为非交易日，已标注至前一交易日 {dates[idx]}'
    else:
        idx = pos

    # 预热窗口上算指标（指标类统一计算），再裁剪回展示窗口 [idx-200, idx+20]
    warm_lo = max(0, idx - BEFORE - buf)
    warm = df.iloc[warm_lo: idx + AFTER + 1].copy()
    warm = _ma_ind.calculate(warm)
    warm = _zx_trend_ind.calculate(warm)
    warm = _zx_bullbear_ind.calculate(warm)
    warm = _mabias_ind.calculate(warm)  # bias7 收盘价相对MA7偏离%

    # 派生指标（与上一交易日对比，%）：vol_pct 量环比、ma7_slope MA7斜率
    def _pct(s):
        return (s.pct_change(fill_method=None) * 100).replace(
            [float('inf'), float('-inf')], float('nan')).round(2)

    warm['vol_pct'] = _pct(warm['volume'])
    warm['ma7_slope'] = _pct(warm['ma7'])

    # 展示窗口前一根收盘价，作为首日涨跌幅基准
    prev_i = idx - BEFORE - 1
    prev_close = round(float(df['close'].iloc[prev_i]), 2) if prev_i >= 0 else None

    show_lo = max(0, idx - BEFORE)
    win = warm.iloc[show_lo - warm_lo:].reset_index(drop=True)

    def ind_list(key):
        return [None if pd.isna(v) else round(float(v), 2) for v in win[key]]

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
        'ma': {k: ind_list(k) for k in IND_KEYS},
        'note': note,
    }
    return jsonify(payload)


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5004)
