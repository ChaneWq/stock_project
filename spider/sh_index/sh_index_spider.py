"""
上证指数数据爬虫模块

功能：
- 爬取上证指数日/周/月K线数据
- 数据来源：搜狐财经
- 输出标准DataFrame

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import re
import json
import pandas as pd
from typing import Dict, Any, Optional
from ..base.base_spider import BaseSpider


class ShIndexSpider(BaseSpider):
    """
    上证指数数据爬虫
    
    数据来源：搜狐财经
    支持指数代码：
        - zs_000001: 上证指数
        - zs_399001: 深证成指
        - zs_399006: 创业板指
    
    使用示例：
        >>> spider = ShIndexSpider()
        >>> df = spider.get_daily('zs_000001', '20260101', '20260624')
        >>> # 返回DataFrame包含 date, open, close, high, low, volume, amount, change_pct
    """
    
    # 搜狐历史数据API
    BASE_URL = 'https://q.stock.sohu.com/hisHq'
    
    # 周期映射
    PERIOD_MAP = {
        'daily': 'd',
        'weekly': 'w',
        'monthly': 'm'
    }
    
    def get_daily(self, code: str = 'zs_000001', start_date: str = '20260101', 
                  end_date: str = '20260624') -> pd.DataFrame:
        """
        获取日线数据
        
        Args:
            code (str): 指数代码，默认'zs_000001'（上证指数）
            start_date (str): 开始日期（格式YYYYMMDD）
            end_date (str): 结束日期（格式YYYYMMDD）
        
        Returns:
            DataFrame: 日线数据
        
        Example:
            >>> df = spider.get_daily('zs_000001', '20260101', '20260624')
        """
        return self._fetch_data(code, start_date, end_date, 'daily')
    
    def get_weekly(self, code: str = 'zs_000001', start_date: str = '20260101', 
                   end_date: str = '20260624') -> pd.DataFrame:
        """
        获取周线数据
        
        Args:
            code (str): 指数代码
            start_date (str): 开始日期（格式YYYYMMDD）
            end_date (str): 结束日期（格式YYYYMMDD）
        
        Returns:
            DataFrame: 周线数据
        """
        return self._fetch_data(code, start_date, end_date, 'weekly')
    
    def get_monthly(self, code: str = 'zs_000001', start_date: str = '20260101', 
                    end_date: str = '20260624') -> pd.DataFrame:
        """
        获取月线数据
        
        Args:
            code (str): 指数代码
            start_date (str): 开始日期（格式YYYYMMDD）
            end_date (str): 结束日期（格式YYYYMMDD）
        
        Returns:
            DataFrame: 月线数据
        """
        return self._fetch_data(code, start_date, end_date, 'monthly')
    
    def _fetch_data(self, code: str, start_date: str, end_date: str, 
                    period_type: str) -> pd.DataFrame:
        """
        获取数据（内部方法）
        
        Args:
            code (str): 指数代码
            start_date (str): 开始日期
            end_date (str): 结束日期
            period_type (str): 周期类型（daily/weekly/monthly）
        
        Returns:
            DataFrame: 标准化数据
        """
        period = self.PERIOD_MAP.get(period_type, 'd')
        
        params = {
            'code': code,
            'start': start_date,
            'end': end_date,
            'stat': 1,
            'order': 'D',
            'period': period,
            'callback': 'historySearchHandler',
            'rt': 'jsonp'
        }
        
        # 发送请求
        response_text = self.fetch_text(self.BASE_URL, params=params)
        
        if not response_text:
            print(f"[ShIndexSpider] 未获取到数据: {code}")
            return pd.DataFrame()
        
        # 解析数据
        try:
            data = self._parse_response(response_text)
            return self._to_dataframe(data)
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            print(f"[ShIndexSpider] 数据解析失败: {e}")
            return pd.DataFrame()
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        解析JSONP响应
        
        搜狐返回格式：historySearchHandler({...});
        
        Args:
            response_text (str): JSONP响应文本
        
        Returns:
            dict: 解析后的数据字典
        """
        match = re.search(r'historySearchHandler\((.*?)\);?$', response_text)
        if not match:
            raise ValueError("无法解析响应数据格式")
        
        json_data = match.group(1)
        data = json.loads(json_data)[0]
        
        return data
    
    def _to_dataframe(self, data: Dict[str, Any]) -> pd.DataFrame:
        """
        转换为标准DataFrame
        
        原始数据格式（data['hq']）：
            [日期, 开盘价, 收盘价, 涨跌额, 涨跌幅, 最低价, 最高价, 成交量, 成交金额, 换手率]
        
        Args:
            data (dict): 解析后的数据
        
        Returns:
            DataFrame: 标准化数据
        
        返回字段：
            - date: 日期
            - open: 开盘价
            - close: 收盘价
            - high: 最高价
            - low: 最低价
            - volume: 成交量
            - amount: 成交金额
            - change_pct: 涨跌幅
        """
        if not data or 'hq' not in data:
            return pd.DataFrame()
        
        hq_data = data['hq']
        
        df = pd.DataFrame(hq_data, columns=[
            'date', 'open', 'close', 'change', 'change_pct',
            'low', 'high', 'volume', 'amount', 'turnover'
        ])
        
        # 数值类型转换
        numeric_cols = ['open', 'close', 'change', 'change_pct', 'low', 'high', 'amount', 'turnover']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # volume转换为整数
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce').astype('Int64')
        
        # 日期转换
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # 选择标准字段
        result = df[['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'change_pct']].copy()
        
        # 按日期升序排列
        result = result.sort_values('date').reset_index(drop=True)
        
        return result
