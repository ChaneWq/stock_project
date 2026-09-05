"""
卖出策略：custom1 止盈卖出，未触发止盈则收盘价卖出

作者：PyStock项目组
日期：2026-09-05
版本：1.0.0
"""

from .base import SellStrategy, SellContext, SellResult


class SellCustom1(SellStrategy):
    """
    custom1 卖出策略

    逻辑：卖出日盘中逐分钟扫描——
        1. 止盈：涨幅（相对买入价）达到 take_profit% → 以该分钟价格卖出
        2. 全天未触发止盈 → 以卖出日收盘价卖出（收盘兜底，非时刻兜底）

    参数（ctx.params）：
        take_profit (float): 止盈涨幅%，如 3 表示 +3%；None 表示不启用
            （不启用时本策略等价于 close 收盘卖）
    """

    name = 'custom1'
    needs_minutes = True

    def determine_sell(self, ctx: SellContext) -> SellResult:
        take_profit = ctx.params.get('take_profit')

        # 盘中逐分钟扫描止盈
        if take_profit is not None:
            for _, row in ctx.minute_df.iterrows():
                pct = (float(row['close']) / ctx.buy_price - 1) * 100
                if pct >= take_profit:
                    time_str = f"{int(row['hour']):02d}:{int(row['minute']):02d}"
                    return SellResult(
                        sell_price=float(row['close']),
                        sell_time=time_str,
                        reason=f'{time_str} 涨至{pct:+.2f}%触发止盈(+{take_profit}%)',
                    )

        # 全天未触发止盈：收盘价卖出
        close_price = float(ctx.sell_day_row['close'])
        return SellResult(
            sell_price=close_price,
            sell_time='close',
            reason='全天未触发止盈，收盘价卖出',
        )
