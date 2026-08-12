"""
爬虫基类模块

功能：
- 提供通用HTTP请求方法
- 提供数据解析工具
- 统一请求头和错误处理

作者：PyStock项目组
日期：2026-06-26
版本：1.0.0
"""

import requests
from typing import Dict, Any, Optional


class BaseSpider:
    """
    爬虫基类
    
    提供通用的HTTP请求和数据解析方法，供具体爬虫继承使用
    
    使用示例：
        >>> class MySpider(BaseSpider):
        >>>     def get_data(self):
        >>>         html = self.fetch_html(url)
        >>>         return self.parse(html)
    """
    
    # 默认请求头
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # JSON请求头
    JSON_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json'
    }
    
    def fetch_html(self, url: str, headers: Dict = None, timeout: int = 10) -> Optional[str]:
        """
        获取HTML内容
        
        Args:
            url (str): 请求URL
            headers (Dict): 请求头，默认使用DEFAULT_HEADERS
            timeout (int): 超时时间（秒）
        
        Returns:
            str: HTML内容，失败返回None
        
        Example:
            >>> html = self.fetch_html('https://example.com')
        """
        final_headers = headers or self.DEFAULT_HEADERS
        
        try:
            response = requests.get(url, headers=final_headers, timeout=timeout)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"[BaseSpider] 请求HTML失败: {e}")
            return None
    
    def fetch_text(self, url: str, params: Dict = None, headers: Dict = None, timeout: int = 10) -> Optional[str]:
        """
        获取响应文本（用于JSONP等）
        
        Args:
            url (str): 请求URL
            params (Dict): 请求参数
            headers (Dict): 请求头
            timeout (int): 超时时间（秒）
        
        Returns:
            str: 响应文本，失败返回None
        
        Example:
            >>> text = self.fetch_text(url, params={'code': 'zs_000001'})
        """
        final_headers = headers or self.JSON_HEADERS
        
        try:
            response = requests.get(url, params=params, headers=final_headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"[BaseSpider] 请求文本失败: {e}")
            return None
