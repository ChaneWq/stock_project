"""
卖出策略插件基类与契约定义

功能：
- SellStrategy: 卖出策略抽象基类（可插拔插件的契约）
- SellContext: 引擎传给策略的上下文数据
- SellResult: 策略返回的卖出结果

设计说明：
- 每个卖出条件 = 一个 SellStrategy 子类 + strategies/__init__.py 注册一行
- 策略通过 needs_minutes 声明是否需要卖出日分时数据，引擎按需拉取
- 与项目指标层（IndicatorBase）同款的类继承风格

作者：PyStock项目组
日期：2026-09-05
版本：1.0.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd


@dataclass
class SellContext:
    """
    卖出决策上下文（引擎构造，传给策略的 determine_sell）

    字段：
        code (str): 股票代码
        buy_price (float): 买入价（flag_date 收盘价）
        buy_date (str): 买入日期 'YYYY-MM-DD'
        sell_date (str): 卖出日期 'YYYY-MM-DD'（下一交易日）
        sell_day_row (Series): 卖出日日线行（含 open/close/high/low/volume 等）
        minute_df (DataFrame): 卖出日分时数据（仅 needs_minutes=True 时提供，
            含 price/volume/hour/minute，vr 策略额外含 volume_ratio）
        params (dict): CLI 透传的策略参数
    """
    code: str
    buy_price: float
    buy_date: str
    sell_date: str
    sell_day_row: pd.Series
    minute_df: Optional[pd.DataFrame] = None
    params: dict = field(default_factory=dict)


@dataclass
class SellResult:
    """
    卖出结果

    字段：
        sell_price (float): 卖出价
        sell_time (str): 卖出时刻（如 '10:02'；日线策略为 'open'/'close'）
        reason (str): 触发原因（如 '涨至+3.00%止盈' / '全天未触发, 收盘兜底'）
    """
    sell_price: float
    sell_time: str
    reason: str


class SellStrategy(ABC):
    """
    卖出策略基类

    使用示例：
        >>> class MySell(SellStrategy):
        ...     name = 'my_sell'
        ...     needs_minutes = True
        ...     def determine_sell(self, ctx: SellContext) -> SellResult:
        ...         ...

    扩展新卖法三步：
        1. strategies/ 下新建文件，实现 SellStrategy 子类
        2. strategies/__init__.py 注册进 STRATEGY_REGISTRY
        3. CLI 使用 --sell my_sell
    """

    # 注册名（CLI --sell 参数使用）
    name: str = ''

    # 是否需要卖出日分时数据（True 时引擎拉取分时后传入 ctx.minute_df）
    needs_minutes: bool = False

    # 是否需要分时量比数据（True 时引擎用 BasicMinutesWithVR 拉取，minute_df 含 volume_ratio）
    needs_vr: bool = False

    @abstractmethod
    def determine_sell(self, ctx: SellContext) -> SellResult:
        """
        决定卖出价格与时刻

        Args:
            ctx (SellContext): 卖出决策上下文

        Returns:
            SellResult: 卖出价格 / 时刻 / 原因
        """
        raise NotImplementedError
