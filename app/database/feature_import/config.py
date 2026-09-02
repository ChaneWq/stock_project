"""
配置读取模块

功能：
- 从同目录 config.ini 读取数据库连接与导入参数
- config.ini 不存在时提示复制模板（密码不入 git）

作者：PyStock项目组
日期：2026-08-31
版本：1.0.0
"""

import os
import configparser

_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_FILE = os.path.join(_CONFIG_DIR, 'config.ini')
_CONFIG_TEMPLATE = os.path.join(_CONFIG_DIR, 'config.ini.example')


def _load_config() -> dict:
    """
    加载配置

    Returns:
        dict: {'db': {...}, 'import': {...}}

    Raises:
        FileNotFoundError: config.ini 不存在
        ValueError: 配置项缺失
    """
    if not os.path.exists(_CONFIG_FILE):
        raise FileNotFoundError(
            f"未找到配置文件 {_CONFIG_FILE}\n"
            f"请复制模板 {_CONFIG_TEMPLATE} 为 config.ini 并填写真实连接信息"
        )

    parser = configparser.ConfigParser()
    parser.read(_CONFIG_FILE, encoding='utf-8')

    if not parser.has_section('database'):
        raise ValueError("config.ini 缺少 [database] 配置节")

    db = {
        'host': parser.get('database', 'host'),
        'port': parser.getint('database', 'port'),
        'user': parser.get('database', 'user'),
        'password': parser.get('database', 'password'),
        'database': parser.get('database', 'database'),
    }
    for key in ('host', 'user', 'password', 'database'):
        if not db[key]:
            raise ValueError(f"config.ini [database] {key} 不能为空")

    default = {
        'table_name': 'stock_features4',
        'stock_list_file': 'sc.txt',
        'date_window_days': 4,
        'bars_offset': 1800,
        'max_workers': 6,
    }
    if parser.has_section('import'):
        for key in default:
            if parser.has_option('import', key):
                value = parser.get('import', key)
                default[key] = int(value) if isinstance(default[key], int) else value

    # 股票清单文件：相对路径按本目录解析
    if not os.path.isabs(default['stock_list_file']):
        default['stock_list_file'] = os.path.join(_CONFIG_DIR, default['stock_list_file'])

    return {'db': db, 'import': default}


# 模块级单例：导入即加载，配置错误尽早暴露
CONFIG = _load_config()
