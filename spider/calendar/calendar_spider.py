"""
日历数据爬虫模块

功能：
- 爬取日历数据（阳历、农历、天干地支、节日）
- 数据来源：bmcx万年历
- 输出标准DataFrame

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import re
import time
import pandas as pd
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import Optional
from ..base.base_spider import BaseSpider


class CalendarSpider(BaseSpider):
    """
    日历数据爬虫
    
    数据来源：bmcx万年历
    爬取内容：阳历日期、农历日期、天干地支、生肖、节日
    
    使用示例：
        >>> spider = CalendarSpider()
        >>> df = spider.get_calendar('2026-01-01', '2026-06-24')
        >>> # 返回DataFrame包含 date, lunar_date, lunar_month, lunar_day, weekday...
    """
    
    # 万年历URL模板
    URL_TEMPLATE = 'https://wannianrili.bmcx.com/{date}__wannianrili/'
    
    def get_calendar(self, start_date: str, end_date: str, delay: float = 0.5) -> pd.DataFrame:
        """
        获取日期范围内的日历数据
        
        Args:
            start_date (str): 开始日期（格式YYYY-MM-DD）
            end_date (str): 结束日期（格式YYYY-MM-DD）
            delay (float): 每次请求间隔（秒），避免请求过快
        
        Returns:
            DataFrame: 日历数据
        
        Example:
            >>> df = spider.get_calendar('2026-01-01', '2026-06-24')
        
        返回字段：
            - date: 阳历日期
            - year: 年
            - month: 月
            - day: 日
            - weekday: 星期
            - lunar_month: 农历月份
            - lunar_day: 农历日期
            - lunar_date: 农历完整日期
            - ganzhi_year: 干支年
            - zodiac_year: 生肖年
            - ganzhi_month: 干支月
            - ganzhi_day: 干支日
            - festival: 节日
        """
        # 生成日期范围
        date_list = self._generate_date_range(start_date, end_date)
        print(f"[CalendarSpider] 将处理 {len(date_list)} 天的数据")
        
        all_data = []
        cached_html = None
        cached_month = None
        
        for i, date in enumerate(date_list):
            # 优化：每月只请求一次（同一月的HTML包含整月数据）
            current_month = date[:7]  # YYYY-MM
            
            if current_month != cached_month:
                # 新月份，请求新HTML
                url = self._build_url(date)
                cached_html = self.fetch_html(url)
                cached_month = current_month
                
                if cached_html:
                    print(f"[CalendarSpider] {i+1}/{len(date_list)} 获取 {current_month} 日历数据")
                else:
                    print(f"[CalendarSpider] {i+1}/{len(date_list)} 获取 {date} 失败")
                
                # 请求间隔
                time.sleep(delay)
            
            # 从缓存的HTML中提取单日数据
            if cached_html:
                calendar_info = self._extract_calendar_info(cached_html, date)
                if calendar_info:
                    all_data.append(calendar_info)
        
        if not all_data:
            print("[CalendarSpider] 未获取到任何数据")
            return pd.DataFrame()
        
        df = pd.DataFrame(all_data)
        print(f"[CalendarSpider] 成功获取 {len(df)} 天的数据")
        
        return df
    
    def get_trade_calendar(self, start_date: str, end_date: str, delay: float = 0.5) -> pd.DataFrame:
        """
        获取交易日历（过滤非交易日）
        
        Args:
            start_date (str): 开始日期（格式YYYY-MM-DD）
            end_date (str): 结束日期（格式YYYY-MM-DD）
            delay (float): 每次请求间隔（秒）
        
        Returns:
            DataFrame: 仅包含交易日的日历数据
        
        Example:
            >>> df = spider.get_trade_calendar('2026-01-01', '2026-06-24')
        """
        df = self.get_calendar(start_date, end_date, delay)
        
        if df.empty:
            return df
        
        # 过滤周末（周六日不交易）
        trade_df = df[~df['weekday'].str.contains('六|日')].copy()
        trade_df = trade_df.reset_index(drop=True)
        
        print(f"[CalendarSpider] 交易日 {len(trade_df)} 天 / 总计 {len(df)} 天")
        
        return trade_df
    
    def _generate_date_range(self, start_date: str, end_date: str) -> list:
        """生成日期范围内的所有日期"""
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        date_list = []
        current = start
        
        while current <= end:
            date_list.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return date_list
    
    def _build_url(self, date_str: str) -> str:
        """构建URL"""
        return self.URL_TEMPLATE.format(date=date_str)
    
    def _extract_calendar_info(self, html_content: str, target_date: str) -> Optional[dict]:
        """
        从HTML内容中提取日历信息
        
        Args:
            html_content (str): HTML内容
            target_date (str): 目标日期（格式YYYY-MM-DD）
        
        Returns:
            dict: 日历信息
        """
        if not html_content:
            return None
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 计算日期在月内的索引
        day = int(target_date.split('-')[2])
        div_id = f'wnrl_k_you_id_{day - 1}'
        
        main_div = soup.find('div', id=div_id)
        
        if not main_div:
            # 尝试备用查找方式
            main_div = soup.find('div', class_='wnrl_k_you')
            if not main_div:
                return None
        
        result = {'date': target_date}
        
        # 解析年、月、星期
        biaoti = main_div.find('div', class_='wnrl_k_you_id_biaoti')
        if biaoti:
            biaoti_text = biaoti.get_text(strip=True)
            match = re.search(r'(\d{4})年\s*(\d{1,2})月\s*\((.*?)\)\s*(星期.*)', biaoti_text)
            if match:
                year, month, _, weekday = match.groups()
                result['year'] = year
                result['month'] = month
                result['weekday'] = weekday
        
        # 解析日
        riqi = main_div.find('div', class_='wnrl_k_you_id_wnrl_riqi')
        if riqi:
            result['day'] = riqi.get_text(strip=True)
        else:
            result['day'] = str(day)
        
        # 解析农历日期
        nongli = main_div.find('div', class_='wnrl_k_you_id_wnrl_nongli')
        if nongli:
            lunar_str = nongli.get_text(strip=True)
            lunar_month, lunar_day = self._parse_lunar_date(lunar_str)
            result['lunar_month'] = lunar_month
            result['lunar_day'] = lunar_day
            result['lunar_date'] = lunar_str
        else:
            result['lunar_month'] = ''
            result['lunar_day'] = ''
            result['lunar_date'] = ''
        
        # 解析干支纪年
        ganzhi = main_div.find('div', class_='wnrl_k_you_id_wnrl_nongli_ganzhi')
        if ganzhi:
            ganzhi_text = ganzhi.get_text(strip=True)
            match = re.search(r'(\S+年)\s*【(\S+)】\s*(\S+月)\s*(\S+日)', ganzhi_text)
            if match:
                gy, zy, gm, gd = match.groups()
                result['ganzhi_year'] = gy.replace('年', '')
                result['zodiac_year'] = zy.replace('年', '')
                result['ganzhi_month'] = gm.replace('月', '')
                result['ganzhi_day'] = gd.replace('日', '')
            else:
                result['ganzhi_year'] = ganzhi_text
                result['zodiac_year'] = ''
                result['ganzhi_month'] = ''
                result['ganzhi_day'] = ''
        else:
            result['ganzhi_year'] = ''
            result['zodiac_year'] = ''
            result['ganzhi_month'] = ''
            result['ganzhi_day'] = ''
        
        # 解析节日
        jieri_div = main_div.find('div', class_='wnrl_k_you_id_wnrl_jieri')
        if jieri_div:
            festivals = [a.get_text(strip=True) for a in jieri_div.find_all('a')]
            result['festival'] = ', '.join(festivals)
        else:
            result['festival'] = ''
        
        return result
    
    def _parse_lunar_date(self, lunar_str: str) -> tuple:
        """解析农历日期，拆分为月份和日期"""
        if not lunar_str:
            return '', ''
        
        match = re.search(r'^(.*?月)(.*)$', lunar_str)
        if match:
            return match.group(1), match.group(2)
        return lunar_str, ''
