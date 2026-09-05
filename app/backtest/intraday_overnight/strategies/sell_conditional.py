"""
卖出策略：止盈/止损/兜底时刻 组合条件卖出

作者：PyStock项目组
日期：2026-09-05
版本：1.0.0
"""

from .base import SellStrategy, SellContext, SellResult


class SellConditional(SellStrategy):
    """
    组合条件卖出策略

    逻辑：卖出日盘中逐分钟扫描，先触发先卖——
        1. 止盈：涨幅（相对买入价）达到 take_profit% → 以该分钟价格卖出
        2. 止损：跌幅达到 stop_loss% → 以该分钟价格卖出
        3. 兜底：全天未触发 → fallback 时刻卖出（默认收盘）

    参数（ctx.params）：
        take_profit (float): 止盈涨幅%，如 3 表示 +3%；None 表示不启用
        stop_loss (float): 止损跌幅%，如 -2 表示 -2%；None 表示不启用
        fallback (str): 兜底时刻 'HH:MM'，默认 '14:57'
    """

    name = 'conditional'
    needs_minutes = True

    def determine_sell(self, ctx: SellContext) -> SellResult:
        take_profit = ctx.params.get('take_profit')
        stop_loss = ctx.params.get('stop_loss')
        fallback = ctx.params.get('fallback', '14:57')

        for _, row in ctx.minute_df.iterrows():
            pct = (float(row['close']) / ctx.buy_price - 1) * 100
            time_str = f"{int(row['hour']):02d}:{int(row['minute']):02d}"

            if take_profit is not None and pct >= take_profit:
                return SellResult(
                    sell_price=float(row['close']),
                    sell_time=time_str,
                    reason=f'{time_str} 涨至{pct:+.2f}%触发止盈(+{take_profit}%)',
                )
            if stop_loss is not None and pct <= stop_loss:
                return SellResult(
                    sell_price=float(row['close']),
                    sell_time=time_str,
                    reason=f'{time_str} 跌至{pct:+.2f}%触发止损({stop_loss}%)',
                )

        # 全天未触发：fallback 时刻兜底
        fh, fm = (int(x) for x in fallback.split(':'))
        target = ctx.minute_df[
            (ctx.minute_df['hour'] > fh)
            | ((ctx.minute_df['hour'] == fh) & (ctx.minute_df['minute'] >= fm))
        ]
        row = (target if not target.empty else ctx.minute_df.tail(1)).iloc[0]
        actual = f"{int(row['hour']):02d}:{int(row['minute']):02d}"
        return SellResult(
            sell_price=float(row['close']),
            sell_time=actual,
            reason=f'全天未触发条件，{fallback}兜底卖出',
        )
