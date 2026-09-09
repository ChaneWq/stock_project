"""
卖出策略：custom2 止盈卖出，未触发止盈则指定时刻卖出

作者：PyStock项目组
日期：2026-09-06
版本：1.0.0
"""

from .base import SellStrategy, SellContext, SellResult


class SellCustom2(SellStrategy):
    """
    custom2 卖出策略

    逻辑：卖出日盘中逐分钟扫描——
        1. 止盈：涨幅（相对买入价）达到 take_profit% → 以该分钟价格卖出
        2. 全天未触发止盈 → 以指定时刻的分钟价格卖出（时刻兜底，与 custom1
           的收盘兜底相对）

    参数（ctx.params）：
        take_profit (float): 止盈涨幅%，如 3 表示 +3%；None 表示不启用
            （不启用时本策略等价于 fixed_time 时刻卖）
        time (str): 未触发止盈时的卖出时刻 HH:MM，默认 10:00
    """

    name = 'custom2'
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

        # 全天未触发止盈：指定时刻卖出
        fallback_time = ctx.params.get('time') or '10:00'
        fh, fm = fallback_time.split(':')
        fh, fm = int(fh), int(fm)

        mask = (ctx.minute_df['hour'] == fh) & (ctx.minute_df['minute'] == fm)
        if not mask.any():
            raise ValueError(f"分时数据中不存在时刻 {fallback_time}")

        row = ctx.minute_df[mask].iloc[0]
        return SellResult(
            sell_price=float(row['close']),
            sell_time=fallback_time,
            reason=f'全天未触发止盈，{fallback_time}时刻卖出',
        )
