"""
卖出策略：次日固定时刻卖出

作者：PyStock项目组
日期：2026-09-05
版本：1.0.0
"""

from .base import SellStrategy, SellContext, SellResult


class SellAtFixedTime(SellStrategy):
    """
    固定时刻卖出策略

    逻辑：卖出日指定时刻按分时价格成交

    参数（ctx.params）：
        time (str): 卖出时刻 'HH:MM'，默认 '10:00'（须在 09:30~14:59 交易时段内）
    """

    name = 'fixed_time'
    needs_minutes = True

    def determine_sell(self, ctx: SellContext) -> SellResult:
        time_str = ctx.params.get('time', '10:00')
        hour, minute = (int(x) for x in time_str.split(':'))

        # 定位目标时刻的分时行（分时按时间升序，取第一条 >= 目标时刻的记录）
        target = ctx.minute_df[
            (ctx.minute_df['hour'] > hour)
            | ((ctx.minute_df['hour'] == hour) & (ctx.minute_df['minute'] >= minute))
        ]
        if target.empty:
            # 目标时刻晚于 14:59 等情况，按最后一分钟兜底
            target = ctx.minute_df.tail(1)

        row = target.iloc[0]
        actual = f"{int(row['hour']):02d}:{int(row['minute']):02d}"
        return SellResult(
            sell_price=float(row['close']),
            sell_time=actual,
            reason=f'固定时刻{time_str}卖出',
        )
