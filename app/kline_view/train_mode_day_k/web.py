"""
训练模式日K Web 服务

读取 signals.csv（code,trade_date 信号日），将信号日K线醒目标注。
与 signal_day_k 的区别：初始只展示到信号日为止，用户点「Next day」
逐日揭晓信号日后的交易日，避免训练时提前看到未来数据。

启动：
    python -m app.kline_view.train_mode_day_k.web
访问：
    http://127.0.0.1:5005/

接口：
    GET  /             渲染页面
    GET  /api/signals  信号清单（读 signals.csv，保持文件顺序）
    GET  /api/kline    查询参数：code + date（信号日 YYYY-MM-DD）+ days_after（已揭晓天数，默认0）
    GET  /api/state    训练账户与历史（启动恢复：现金/全局账本/个股会话历史）
    GET  /api/stats    训练成绩统计（总览卡片/按日盈亏/按股票汇总/每笔明细）
    POST /api/session  结束训练上报：{code,start,final,ts,trades} 追加会话记录并更新现金账本
    POST /api/reset    重置账户：现金回初始、清空账本与历史
"""

import bisect
import json
import os
import sys

import pandas as pd
from flask import Flask, render_template, jsonify, request

# 兼容两种启动方式（惯例同 demo_day_k / signal_day_k）
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
AFTER = 20         # 信号日后最多可揭晓（Next day）的交易日数

# 展示指标键（payload.ma 与前端约定一致；vol_pct/ma7_slope/bias7 为派生指标，仅面板显示值不画线）
IND_KEYS = ('ma7', 'zx_short_term_trend', 'zx_bull_bear_line', 'vol_pct', 'ma7_slope', 'bias7')

# 指标实例创建一次复用（工程惯例，避免每请求重复实例化）
_ma_ind = MAIndicator(periods=[MA_PERIOD])
_zx_trend_ind = ZXShortTermTrendIndicator()
_zx_bullbear_ind = ZXBullBearLineIndicator()
_mabias_ind = MABiasIndicator()  # 默认 periods=[7] → bias7

_SIGNALS_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'signals.csv')

# ===== 训练记录持久化（本地 JSON，不入 git；单用户训练平台，模块级加载+落盘时写文件） =====
INIT_CASH = 100000.0
_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'train_history.json')


def _empty_state():
    return {'cash': INIT_CASH, 'trades': [], 'history': {}}


def _load_state():
    if not os.path.exists(_STATE_FILE):
        return _empty_state()
    try:
        with open(_STATE_FILE, encoding='utf-8') as f:
            st = json.load(f)
        return {
            'cash': float(st.get('cash', INIT_CASH)),
            'trades': st.get('trades') or [],
            'history': st.get('history') or {},
        }
    except Exception:
        return _empty_state()  # 文件损坏时按空状态启动，不阻塞训练


_STATE = _load_state()


def _save_state():
    with open(_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(_STATE, f, ensure_ascii=False, indent=1)


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


@app.route('/api/state')
def api_state():
    """训练账户与历史：页面启动时恢复（现金/全局账本/个股会话历史）"""
    return jsonify(_STATE)


@app.route('/api/stats')
def api_stats():
    """训练成绩统计：遍历全局账本 Buy→Sell 配对（会话必清仓，配对可靠），未平仓不计入"""
    trades = _STATE.get('trades') or []
    cash = float(_STATE.get('cash', INIT_CASH))

    pairs = []  # 每笔完成交易：{code, buy_date, buy_price, sell_date, sell_price, shares, pnl, pnl_pct, hold}
    buy = None
    for t in trades:
        if t.get('side') == 'Buy':
            buy = t  # 全仓买卖，同时只会有一笔持仓
        elif t.get('side') == 'Sell' and buy:
            amount_diff = round(float(t['amount']) - float(buy['amount']), 2)
            pnl_pct = round(amount_diff / float(buy['amount']) * 100, 2)
            pairs.append({
                'code': t.get('code') or buy.get('code') or '',
                'buy_date': buy['date'], 'buy_price': buy['price'],
                'sell_date': t['date'], 'sell_price': t['price'],
                'shares': t['shares'],
                'pnl': amount_diff, 'pnl_pct': pnl_pct,
                'hold': int(t.get('index', 0)) - int(buy.get('index', 0)),
            })
            buy = None

    wins = [p for p in pairs if p['pnl'] > 0]
    losses = [p for p in pairs if p['pnl'] < 0]
    total_win = round(sum(p['pnl'] for p in wins), 2)
    total_loss = round(-sum(p['pnl'] for p in losses), 2)
    avg_hold = round(sum(p['hold'] for p in pairs) / len(pairs), 1) if pairs else 0

    # 按日期盈亏：盈亏归属 Sell 平仓日，同日多股合并，累计自首笔平仓日起
    daily_map = {}
    for p in pairs:
        d = daily_map.setdefault(p['sell_date'], {'count': 0, 'pnl': 0.0})
        d['count'] += 1
        d['pnl'] = round(d['pnl'] + p['pnl'], 2)
    daily, cum = [], 0.0
    for date in sorted(daily_map):
        cum = round(cum + daily_map[date]['pnl'], 2)
        daily.append({'date': date, 'count': daily_map[date]['count'],
                      'pnl': daily_map[date]['pnl'], 'cum': cum})

    # 按月盈亏幅度：当月平仓盈亏 / 月初总资产（初始资金+此前累计盈亏），复用日度聚合
    month_map = {}
    for d in daily:
        m = month_map.setdefault(d['date'][:7], {'count': 0, 'pnl': 0.0})
        m['count'] += d['count']
        m['pnl'] = round(m['pnl'] + d['pnl'], 2)
    monthly, mcum = [], 0.0
    for month in sorted(month_map):
        base = INIT_CASH + mcum  # 月初总资产
        mcum = round(mcum + month_map[month]['pnl'], 2)
        monthly.append({
            'month': month,
            'count': month_map[month]['count'],
            'pnl': month_map[month]['pnl'],
            'pct': round(month_map[month]['pnl'] / base * 100, 2) if base > 0 else None,
            'cum_pct': round(mcum / INIT_CASH * 100, 2),
        })

    # 按股票汇总（含资金加权收益率/胜率/平均持有，供前端交易个股表排序回看）
    stock_map = {}
    for p in pairs:
        s = stock_map.setdefault(p['code'], {'count': 0, 'wins': 0, 'pnl': 0.0,
                                             'amount': 0.0, 'hold': 0})
        s['count'] += 1
        if p['pnl'] > 0:
            s['wins'] += 1
        s['pnl'] = round(s['pnl'] + p['pnl'], 2)
        s['amount'] += p['shares'] * p['buy_price']
        s['hold'] += p['hold']
    stocks = [{'code': c, 'count': s['count'], 'wins': s['wins'],
               'losses': s['count'] - s['wins'],
               'win_rate': round(s['wins'] / s['count'] * 100, 1),
               'pnl': s['pnl'],
               'pct': round(s['pnl'] / s['amount'] * 100, 2) if s['amount'] > 0 else None,
               'avg_hold': round(s['hold'] / s['count'], 1)}
              for c, s in sorted(stock_map.items(), key=lambda kv: -kv[1]['pnl'])]

    total_pnl = round(cash - INIT_CASH, 2)
    return jsonify({
        'init_cash': INIT_CASH,
        'cash': round(cash, 2),
        'total_pnl': total_pnl,
        'total_pct': round(total_pnl / INIT_CASH * 100, 2),
        'count': len(pairs),
        'wins': len(wins), 'losses': len(losses),
        'win_rate': round(len(wins) / len(pairs) * 100, 1) if pairs else 0,
        'avg_win': round(total_win / len(wins), 2) if wins else 0,
        'avg_loss': round(total_loss / len(losses), 2) if losses else 0,
        # 单笔收益率口径的平均幅度（与金额口径 avg_win/avg_loss 对应，亏损为负值）
        'avg_win_pct': round(sum(p['pnl_pct'] for p in wins) / len(wins), 2) if wins else 0,
        'avg_loss_pct': round(sum(p['pnl_pct'] for p in losses) / len(losses), 2) if losses else 0,
        'pl_ratio': round(total_win / total_loss, 2) if total_loss > 0 else None,
        'avg_hold': avg_hold,
        'stocks_trained': len(stock_map),
        'best': max(pairs, key=lambda p: p['pnl_pct']) if pairs else None,
        'worst': min(pairs, key=lambda p: p['pnl_pct']) if pairs else None,
        'daily': daily,
        'monthly': monthly,
        'stocks': stocks,
        'details': pairs,
    })


@app.route('/api/session', methods=['POST'])
def api_session():
    """结束训练上报：追加该股会话记录，并更新持久化的现金与全局账本"""
    data = request.get_json(silent=True) or {}
    code = str(data.get('code') or '').strip()
    try:
        start = round(float(data.get('start')), 2)
        final = round(float(data.get('final')), 2)
    except (TypeError, ValueError):
        return jsonify({'error': 'start/final 须为数字'}), 400
    trades = data.get('trades') or []
    if not code or not isinstance(trades, list):
        return jsonify({'error': 'code/trades 缺失或非法'}), 400
    _STATE.setdefault('history', {}).setdefault(code, []).append({
        'ts': str(data.get('ts') or ''),
        'signal_date': str(data.get('signal_date') or ''),
        'start': start,
        'final': final,
        'trades': trades,
    })
    _STATE['cash'] = final
    _STATE.setdefault('trades', []).extend(trades)
    try:
        _save_state()
    except Exception as e:
        return jsonify({'error': f'保存训练记录失败：{e}'}), 500
    return jsonify({'ok': True})


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """重置账户：现金回初始、清空账本与全部个股训练历史"""
    _STATE.update(_empty_state())
    try:
        _save_state()
    except Exception as e:
        return jsonify({'error': f'保存重置状态失败：{e}'}), 500
    return jsonify({'ok': True})


def _signal_trained(code, signal_date):
    """(code, 信号日) 维度已训练判定：同一股票的第二次信号不受第一次训练影响。

    旧数据兼容：train_history.json 中无 signal_date 字段的旧会话无法区分训练的是
    哪个信号，若该股全部会话均为旧记录则保守回退 code 级判定（视为已训练防偷看）；
    混合场景（新旧并存）按新记录精确匹配，缺匹配视为未训练（安全方向=继续裁剪）。
    """
    sessions = _STATE.get('history', {}).get(code) or []
    if not sessions:
        return False
    if any(s.get('signal_date') == signal_date for s in sessions):
        return True
    return all(not s.get('signal_date') for s in sessions)


@app.route('/api/kline')
def api_kline():
    """训练模式K线接口：信号日前200个交易日 ~ 信号日后 days_after 个交易日

    后端裁剪保证不泄露未来数据：返回的 dates/candle/ma 只到 信号日+days_after，
    other_signals 过滤掉可见范围外的未来信号日。
    """
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

    # 已揭晓天数：clamp 到 [0, AFTER]，防止越参偷看
    try:
        days_after = int(request.args.get('days_after', 0))
    except (TypeError, ValueError):
        days_after = 0
    days_after = max(0, min(AFTER, days_after))

    # 已训练信号全量开放（防偷看仅对未训练信号生效；判定以持久化历史为准，前端无法绕过）
    trained = _signal_trained(code, signal_date)
    if trained:
        days_after = AFTER

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

    # 预热窗口上算指标（指标类统一计算），再裁剪回展示窗口 [idx-200, idx+days_after]
    # 注意：指标计算窗口不随 days_after 变化，保证同一信号任何揭晓阶段指标值一致
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
    # 训练模式核心裁剪：只返回到 信号日+days_after（get_daily 有缓存，逐日揭晓毫秒级命中）
    end_abs = min(idx + days_after, len(df) - 1)
    win = warm.iloc[show_lo - warm_lo: end_abs - warm_lo + 1].reset_index(drop=True)

    def ind_list(key):
        return [None if pd.isna(v) else round(float(v), 2) for v in win[key]]

    # 同 code 其它信号日落在可见范围内的索引（前端弱标注；未来信号日不泄露）
    other_idx = []
    try:
        for s in load_signals():
            if s['code'] == code and s['trade_date'] != dates[idx]:
                p = bisect.bisect_left(dates, s['trade_date'])
                if p < len(dates) and dates[p] == s['trade_date'] and show_lo <= p <= end_abs:
                    other_idx.append(p - show_lo)
    except Exception:
        pass

    payload = {
        'code': code,
        'signal_date': dates[idx],
        'signal_index': idx - show_lo,
        'trained': trained,
        'days_after': days_after,
        'max_after': AFTER,
        # 是否还有下一交易日可揭晓（只告知有无，不告知剩余总数，避免间接泄露未来窗口大小）
        'has_more_after': len(dates) - 1 > idx + days_after,
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
    app.run(debug=True, host='127.0.0.1', port=5005)
