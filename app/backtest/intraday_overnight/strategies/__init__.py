"""
卖出策略注册表

扩展新卖法三步：
    1. 本目录新建文件实现 SellStrategy 子类
    2. 下方 import 并加入 STRATEGY_REGISTRY
    3. CLI 使用 --sell <name>
"""

from .base import SellStrategy, SellContext, SellResult
from .sell_open import SellAtOpen
from .sell_close import SellAtClose
from .sell_fixed_time import SellAtFixedTime
from .sell_conditional import SellConditional
from .sell_vr import SellOnVR

# 注册表：name → 策略实例（无状态，模块级复用）
STRATEGY_REGISTRY = {
    'open': SellAtOpen(),
    'close': SellAtClose(),
    'fixed_time': SellAtFixedTime(),
    'conditional': SellConditional(),
    'vr': SellOnVR(),
}
