# strategies/__init__.py - 策略注册
from .vr_slope import evaluate as vr_slope_evaluate
from .vr_anomaly import evaluate as vr_anomaly_evaluate

STRATEGIES = {
    'vr_slope': vr_slope_evaluate,
    'vr_anomaly': vr_anomaly_evaluate,
}


def get_strategy(strategy_id):
    """根据策略ID获取evaluate函数"""
    if strategy_id not in STRATEGIES:
        raise ValueError(f"未知策略: {strategy_id}，可用策略: {list(STRATEGIES.keys())}")
    return STRATEGIES[strategy_id]


def list_strategies():
    """列出所有可用策略"""
    return list(STRATEGIES.keys())
