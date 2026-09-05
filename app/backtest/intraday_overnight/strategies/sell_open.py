"""
卖出策略：次日开盘价卖出

作者：PyStock项目组
日期：2026-09-05
版本：1.0.0
"""

from .base import SellStrategy, SellContext, SellResult


class SellAtOpen(SellStrategy):
    """
    开盘卖出策略

    逻辑：卖出日开盘价成交（隔夜情绪兑现，持有约18小时）
    """

    name = 'open'
    needs_minutes = False

    def determine_sell(self, ctx: SellContext) -> SellResult:
        return SellResult(
            sell_price=float(ctx.sell_day_row['open']),
            sell_time='open',
            reason='次日开盘卖出',
        )
