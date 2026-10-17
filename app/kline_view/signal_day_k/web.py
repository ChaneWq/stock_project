"""
信号复盘台 Web 服务

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
    GET  /api/notes   备注清单（键 code|date，与分组无关全局共享）
    POST /api/notes   保存备注（JSON: code, date, note；note 空白=删除该信号备注）
    GET  /api/export  一键导出：分组/标记/书签/备注/信号清单打包单 JSON 附件下载
    POST /api/import  一键导入：上传备份 JSON（form: file + mode=merge|replace + import_signals），
                      可选将备份中的信号清单并入 data/signals.csv（去重保序只增不减）；
                      导入前自动备份当前数据到 data/review_data.json.import_bak
"""

import bisect
import csv
import json
import os
import re
import sys
from datetime import datetime
from urllib.parse import quote

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

_SIGNALS_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'signals.csv')


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


# 分组/标记/书签/备注/信号清单等数据文件统一集中存放在 data/ 子目录（本地配置，不入 git）；
# "全部"为内置虚拟分组不落文件。旧版双文件（模块根目录 groups.json + notes.json）
# 在新文件缺失时自动合并迁移到 data/review_data.json（旧文件改名 .migrated 保留）
_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(_DATA_DIR, exist_ok=True)
_DATA_JSON = os.path.join(_DATA_DIR, 'review_data.json')
_LEGACY_GROUPS_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'groups.json')
_LEGACY_NOTES_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'notes.json')


def _load_json_file(path):
    """读 JSON 文件；缺失/损坏返回 None，不报错（由调用方决定回退）"""
    if not os.path.exists(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _sanitize_data(data):
    """清洗数据：分组去重保序，剔除指向不存在分组的标记/书签与空白备注（惯例同旧 load_groups）"""
    groups = list(dict.fromkeys(str(g) for g in data.get('groups', []) if str(g).strip()))
    tags = {}
    for k, v in (data.get('tags') or {}).items():
        if isinstance(v, list):
            vals = [str(g) for g in v if g in groups]
            if vals:
                tags[str(k)] = vals
    bookmarks = {}
    for k, v in (data.get('bookmarks') or {}).items():
        k, v = str(k), str(v)
        if (k in groups or k == '全部') and '|' in v:
            bookmarks[k] = v
    notes = {str(k): str(v) for k, v in (data.get('notes') or {}).items() if str(v).strip()}
    return {'groups': groups, 'tags': tags, 'bookmarks': bookmarks, 'notes': notes}


def _migrate_legacy():
    """一次性迁移：旧版 groups.json + notes.json 合并生成 review_data.json，旧文件改名 .migrated"""
    lg = _load_json_file(_LEGACY_GROUPS_JSON) or {}
    ln = _load_json_file(_LEGACY_NOTES_JSON) or {}
    data = _sanitize_data({'groups': lg.get('groups', []), 'tags': lg.get('tags', {}),
                           'bookmarks': lg.get('bookmarks', {}), 'notes': ln})
    save_data(data)
    for p in (_LEGACY_GROUPS_JSON, _LEGACY_NOTES_JSON):
        if os.path.exists(p):
            try:
                os.replace(p, p + '.migrated')
            except OSError:
                pass
    return data


def load_data():
    """读全量数据；新文件缺失先做旧版迁移，损坏回退空结构（不覆盖坏文件，留待人工检查）"""
    if not os.path.exists(_DATA_JSON):
        return _migrate_legacy()
    raw = _load_json_file(_DATA_JSON)
    if raw is None:
        return {'groups': [], 'tags': {}, 'bookmarks': {}, 'notes': {}}
    return _sanitize_data(raw)


def save_data(data):
    """落盘（先写临时文件再替换，避免写一半损坏）"""
    tmp = _DATA_JSON + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _DATA_JSON)


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
        d = load_data()
        return jsonify({'groups': d['groups'], 'tags': d['tags'], 'bookmarks': d['bookmarks']})

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': '分组名不能为空'}), 400
    if name == '全部':
        return jsonify({'error': '"全部"为内置分组，不能创建或删除'}), 400

    d = load_data()
    if request.method == 'POST':
        if name in d['groups']:
            return jsonify({'error': f'分组「{name}」已存在'}), 400
        d['groups'].append(name)
        save_data(d)
        return jsonify({'ok': True})

    # DELETE：删除分组并清理所有信号上该组标记与该书签
    if name not in d['groups']:
        return jsonify({'error': f'分组「{name}」不存在'}), 404
    d['groups'].remove(name)
    d['tags'] = {k: [t for t in v if t != name] for k, v in d['tags'].items()}
    d['tags'] = {k: v for k, v in d['tags'].items() if v}
    d['bookmarks'].pop(name, None)
    save_data(d)
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

    d = load_data()
    unknown = [x for x in groups if x not in d['groups']]
    if unknown:
        return jsonify({'error': f'分组不存在：{",".join(unknown)}'}), 400

    key = f'{code}|{date}'
    if groups:
        d['tags'][key] = groups
    else:
        d['tags'].pop(key, None)
    # 信号被移出分组时，级联清除指向该信号的书签（"全部"书签不受标记影响）
    for grp in list(d['bookmarks']):
        if grp != '全部' and d['bookmarks'][grp] == key and grp not in d['tags'].get(key, []):
            del d['bookmarks'][grp]
    save_data(d)
    return jsonify({'ok': True})


@app.route('/api/bookmark', methods=['POST', 'DELETE'])
def api_bookmark():
    """分组书签：POST 标记（书签只前进，新位置更前时保留原书签）/ DELETE 取消"""
    data = request.get_json(silent=True) or {}
    group = (data.get('group') or '').strip()
    if not group:
        return jsonify({'error': '缺少 group 参数'}), 400

    d = load_data()
    if group != '全部' and group not in d['groups']:
        return jsonify({'error': f'分组「{group}」不存在'}), 404

    if request.method == 'DELETE':
        d['bookmarks'].pop(group, None)
        save_data(d)
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

    old = d['bookmarks'].get(group)
    if old and old in keys and keys.index(old) > keys.index(key):
        return jsonify({'ok': True, 'kept': True, 'key': old})   # 保留更靠后的原书签
    d['bookmarks'][group] = key
    save_data(d)
    return jsonify({'ok': True, 'kept': False, 'key': key})


@app.route('/api/notes', methods=['GET', 'POST'])
def api_notes():
    """信号备注：GET 全量清单 / POST 保存（note 空白=删除；键 code|date，与分组无关）"""
    if request.method == 'GET':
        return jsonify(load_data()['notes'])

    data = request.get_json(silent=True) or {}
    code = (data.get('code') or '').strip()
    date = (data.get('date') or '').strip()
    note = (data.get('note') or '').strip()
    if not code or not date:
        return jsonify({'error': '缺少 code/date 参数'}), 400
    if len(note) > 2000:
        return jsonify({'error': '备注最长 2000 字'}), 400

    d = load_data()
    key = f'{code}|{date}'
    if note:
        d['notes'][key] = note
    else:
        d['notes'].pop(key, None)
    save_data(d)
    return jsonify({'ok': True, 'deleted': not note})


# ===================== 数据导入导出 =====================
# 分组/标记/书签/备注统一存于 review_data.json：导出打包单 JSON 下载、导入整体写回
# （signals.csv 信号清单不参与导入导出，属信号源另行走维护流程）


def _validate_import(raw):
    """导入文件结构校验：通过返回 None，否则返回错误文案（先校验后写盘，绝不半截导入）。
    兼容直接导入存储文件 review_data.json（无 version/signals 头，四项结构同 v1）"""
    if not isinstance(raw, dict):
        return '备份文件结构异常：顶层须为 JSON 对象'
    for field, typ in (('groups', list), ('tags', dict), ('bookmarks', dict), ('notes', dict)):
        if not isinstance(raw.get(field), typ):
            return f'备份文件缺少字段或类型不符：{field}'
    ver = raw.get('version')
    if ver is not None:
        if not isinstance(ver, int) or isinstance(ver, bool):
            return '备份文件 version 须为整数'
        if ver > 1:
            return f'备份文件版本过新（v{ver}），请先升级程序后再导入'
    if 'signals' in raw and not isinstance(raw.get('signals'), list):
        return '备份文件字段类型不符：signals'
    return None


@app.route('/api/export')
def api_export():
    """一键导出：分组/标记/书签/备注/信号清单打包为单 JSON 附件下载"""
    d = load_data()
    now = datetime.now()
    payload = {
        'version': 1,
        'app': 'signal_day_k',
        'exported_at': now.strftime('%Y-%m-%d %H:%M:%S'),
        'signals': load_signals(),
        'groups': d['groups'],
        'tags': d['tags'],
        'bookmarks': d['bookmarks'],
        'notes': d['notes'],
    }
    fname = f'复盘备份_{now.strftime("%Y%m%d_%H%M%S")}.json'
    resp = jsonify(payload)
    # ASCII 回退名 + RFC5987 UTF-8 名，中文文件名各浏览器兼容
    resp.headers['Content-Disposition'] = (
        f"attachment; filename=\"signal_backup.json\"; filename*=UTF-8''{quote(fname)}")
    return resp


@app.route('/api/import', methods=['POST'])
def api_import():
    """一键导入：上传备份 JSON（form: file + mode=merge 合并 / replace 覆盖还原）。
    导入前自动备份当前数据到 review_data.import_bak.json（覆盖上一次），误导入可回滚"""
    file = request.files.get('file')
    if file is None or not file.filename:
        return jsonify({'error': '请选择备份 JSON 文件'}), 400
    mode = request.form.get('mode') or 'merge'
    if mode not in ('merge', 'replace'):
        return jsonify({'error': 'mode 须为 merge 或 replace'}), 400

    try:
        raw = json.loads(file.read().decode('utf-8-sig'))
    except Exception:
        return jsonify({'error': '文件不是有效的 JSON'}), 400
    err = _validate_import(raw)
    if err:
        return jsonify({'error': err}), 400
    imp = _sanitize_data(raw)   # 规范化备份内容（剔除引用不存在分组的标记等）

    # 备份中的信号清单（可选，老格式/存储文件无此字段）：仅保留 code/trade_date 非空项并去重保序
    imp_signals = []
    for s in raw.get('signals') or []:
        if isinstance(s, dict):
            c, dt = str(s.get('code') or '').strip(), str(s.get('trade_date') or '').strip()
            if c and dt:
                imp_signals.append({'code': c, 'trade_date': dt})
    # 标记/备注/书签键中出现的信号也一并并入：备份的 signals 数组只反映导出当时的 signals.csv，
    # 而标记对应的信号可能不在其中（如清单被重置过），不反推会导致导入后标记"看不见"
    _seen_sig = {(s['code'], s['trade_date']) for s in imp_signals}
    for key in list(imp['tags']) + list(imp['notes']) + list(imp['bookmarks'].values()):
        c, _, dt = str(key).partition('|')
        c, dt = c.strip(), dt.strip()
        if c and re.match(r'\d{4}-\d{2}-\d{2}$', dt) and (c, dt) not in _seen_sig:
            _seen_sig.add((c, dt))
            imp_signals.append({'code': c, 'trade_date': dt})
    # 防御：参数缺失（如浏览器缓存旧前端）时默认合并信号清单，显式传 '0'（取消勾选）才跳过
    want_signals = request.form.get('import_signals', '1') != '0'

    # 可选：备份信号清单并入 signals.csv（去重保序只增不减，本地已有顺序不动）
    # signals.csv 除 code,trade_date 外可能还有统计列：原行整行保留，追加行统计列留空
    added_signals = 0
    if want_signals and imp_signals:
        try:
            with open(_SIGNALS_CSV, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                rows = []
                seen = set()
                for row in reader:
                    if len(row) >= 2 and row[0].strip() and row[1].strip():
                        rows.append(row)
                        seen.add((row[0].strip(), row[1].strip()))
        except FileNotFoundError:
            header, rows, seen = None, [], set()
        except Exception as e:
            return jsonify({'error': f'读取 signals.csv 失败：{e}'}), 500
        add = [s for s in imp_signals if (s['code'], s['trade_date']) not in seen]
        if add:
            ncols = len(header) if header else 2
            out = ([header] if header else [['code', 'trade_date']]) + rows
            out += [[s['code'], s['trade_date']] + [''] * (ncols - 2) for s in add]
            tmp = _SIGNALS_CSV + '.tmp'
            with open(tmp, 'w', encoding='utf-8-sig', newline='') as f:
                csv.writer(f).writerows(out)
            os.replace(tmp, _SIGNALS_CSV)
        added_signals = len(add)

    cur = load_data()
    # 导入前自动备份当前全量数据（先写临时文件再替换，防写一半）
    tmp = _DATA_JSON + '.import_bak.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(cur, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _DATA_JSON + '.import_bak')

    if mode == 'replace':
        # 覆盖还原：分组/标记/书签/备注整体替换为备份内容（signals.csv 只做追加合并，不替换）
        save_data(imp)
        return jsonify({'ok': True, 'stats': {
            'mode': mode, 'added_groups': len(imp['groups']),
            'imported_tags': len(imp['tags']), 'imported_notes': len(imp['notes']),
            'bookmarks_set': len(imp['bookmarks']), 'bookmarks_kept': 0,
            'added_signals': added_signals}})

    # 合并：groups 取并集按备份顺序追加；tags/notes 同键以导入为准；
    # bookmarks 冲突取 signals.csv 顺序更靠后的键（延续"只前进"），键不在清单视为最前不覆盖现值
    try:
        keys = [f"{s['code']}|{s['trade_date']}" for s in load_signals()]
    except Exception:
        keys = []

    def _pos(key):
        return keys.index(key) if key in keys else -1

    new_groups = cur['groups'] + [g for g in imp['groups'] if g not in cur['groups']]
    new_tags = {**cur['tags'], **imp['tags']}
    new_notes = {**cur['notes'], **imp['notes']}

    new_bm = dict(cur['bookmarks'])
    bm_set = bm_kept = 0
    for grp, key in imp['bookmarks'].items():
        if grp != '全部' and grp not in new_groups:
            continue
        if grp in new_bm and _pos(new_bm[grp]) >= _pos(key):
            bm_kept += 1   # 现书签更靠后，保留
            continue
        new_bm[grp] = key
        bm_set += 1

    save_data({'groups': new_groups, 'tags': new_tags,
               'bookmarks': new_bm, 'notes': new_notes})
    return jsonify({'ok': True, 'stats': {
        'mode': mode, 'added_groups': len(new_groups) - len(cur['groups']),
        'imported_tags': len(imp['tags']), 'imported_notes': len(imp['notes']),
        'bookmarks_set': bm_set, 'bookmarks_kept': bm_kept,
        'added_signals': added_signals}})


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
