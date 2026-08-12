"""
股票监控列表配置（CSV 读取）

CSV 文件：与本文件同目录的 stocks.csv
CSV 列：code,name,remark
    code:   6位股票代码
    name:   股票名称
    remark: 备注（可选，用户自定义）
"""

import csv
import os

CSV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'stocks.csv')


def load_stocks():
    """
    读取 stocks.csv 返回股票列表

    Returns:
        list[dict]: [{'code','name','remark'}, ...]
    """
    stocks = []
    if not os.path.exists(CSV_PATH):
        print(f"[stocks] CSV 文件不存在: {CSV_PATH}")
        return stocks

    # utf-8-sig 兼容带 BOM / 不带 BOM 的 UTF-8（Excel 另存为 UTF-8 也兼容）
    with open(CSV_PATH, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = (row.get('code') or '').strip()
            name = (row.get('name') or '').strip()
            remark = (row.get('remark') or '').strip()
            if not code:
                continue
            stocks.append({'code': code, 'name': name, 'remark': remark})
    return stocks
