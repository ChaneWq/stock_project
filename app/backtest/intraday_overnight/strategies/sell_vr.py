"""
卖出策略：量比触发卖出

作者：PyStock项目组
日期：2026-09-05
版本：1.0.0
"""

from .base import SellStrategy, SellContext, SellResult


class SellOnVR(SellStrategy):
    """
    量比触发卖出策略

    逻辑：卖出日盘中量比首次达到阈值时卖出（放量兑现），
        全天未达到则收盘兜底

    参数（ctx.params）：
        vr (float): 量比阈值，默认 2.5
        fallback (str): 兜底时刻 'HH:MM'，默认 '14:57'

    数据说明：
        minute_df 由引擎通过 BasicMinutesWithVR 获取，含 volume_ratio 列
    """

    name = 'vr'
    needs_minutes = True
    needs_vr = True

    def determine_sell(self, ctx: SellContext) -> SellResult:
        vr_threshold = float(ctx.params.get('vr', 2.5))
        fallback = ctx.params.get('fallback', '14:57')

        for _, row in ctx.minute_df.iterrows():
            vr = row.get('volume_ratio')
            if vr is None or vr != vr:  # NaN 跳过
                continue
            if float(vr) >= vr_threshold:
                time_str = f"{int(row['hour']):02d}:{int(row['minute']):02d}"
                return SellResult(
                    sell_price=float(row['close']),
                    sell_time=time_str,
                    reason=f'{time_str} 量比{float(vr):.2f}达到阈值{vr_threshold}卖出',
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
            sell_price=float(row['price']),
            sell_time=actual,
            reason=f'全天量比未达{vr_threshold}，{fallback}兜底卖出',
        )
