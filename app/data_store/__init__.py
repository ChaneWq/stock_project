"""
本地数据落地（SQLite）

对外接口：
    >>> from app.data_store import get_daily      # 透传+回写读取日线
    >>> from app.data_store import sync_daily     # 增量同步
    >>> from app.data_store import load_daily     # 纯本地读取
"""

from .store import get_daily, load_daily, save_daily, get_latest_date
from .sync import sync_daily

__all__ = ['get_daily', 'load_daily', 'save_daily', 'get_latest_date', 'sync_daily']
