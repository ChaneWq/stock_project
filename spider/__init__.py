"""
爬虫子项目包初始化文件

导出爬虫类供外部使用
"""

from .base.base_spider import BaseSpider
from .calendar.calendar_spider import CalendarSpider
from .sh_index.sh_index_spider import ShIndexSpider

__all__ = ['BaseSpider', 'CalendarSpider', 'ShIndexSpider']