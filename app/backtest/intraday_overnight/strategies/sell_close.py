"""
卖出策略：次日收盘价卖出（默认兜底口径）

作者：PyStock项目组
日期：2026-09-05
版本：1.0.0
"""

from .base import SellStrategy, SellContext, SellResult


class SellAtClose(SellStrategy):
    """
    收盘卖出策略

    逻辑：卖出日收盘价成交（持有整个次日交易日）
    """

    name = 'close'
    needs_minutes = False

    def determine_sell(self, ctx: SellContext) -> SellResult:
        return SellResult(
            sell_price=float(ctx.sell_day_row['close']),
            sell_time='close',
            reason='次日收盘卖出',
        )
