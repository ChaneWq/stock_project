# PyStock数据层

## 项目简介

PyStock数据层是一个专注于股票数据获取和技术指标计算的Python数据层，提供标准化的数据访问接口。

## 核心特点

- **分层架构**：数据源层 + 基础数据层 + 指标数据层
- **统一输出**：所有数据返回标准DataFrame
- **易于扩展**：模块化设计，新增功能简单

## 快速开始

### 安装依赖

```bash
pip install pandas mootdx numpy
```

### 基础使用

```python
from pystock_data import BasicBars, BasicMinutes

# 获取日线数据
bars = BasicBars()
day_df = bars.get_daily('000400', 100)

# 获取分时数据
minutes = BasicMinutes()
minute_df = minutes.get_data('000400', '20260624')
```

### 指标计算

```python
from pystock_data import BasicBars, KDJIndicator, MACDIndicator

bars = BasicBars()
kdj = KDJIndicator()
macd = MACDIndicator()

# 获取基础数据
basic_df = bars.get_daily('000400', 100)

# 计算KDJ指标
kdj_df = kdj.calculate(basic_df)

# 计算MACD指标
macd_df = macd.calculate(basic_df)

# 组合多个指标
enhanced_df = kdj.calculate(basic_df)
enhanced_df = macd.calculate(enhanced_df)  # 再添加MACD字段
```

## 示例代码

查看 [examples/](examples/) 目录获取更多使用示例：

- **quick_test.py**：快速功能演示，展示数据层的所有核心功能
  ```bash
  python examples/quick_test.py
  ```

## 测试

运行测试套件验证功能：

```bash
pytest pystock_data/tests/ -v
```

## 主要功能

### 基础数据层
- **BasicBars**：日线、周线、月线数据
- **BasicMinutes**：分时数据（分钟级）

### 指标数据层
- **KDJIndicator**：KDJ随机指标
- **MACDIndicator**：MACD异同移动平均线
- **MAIndicator**：均线指标（MA5、MA10、MA20等）
- **VolumeRatioIndicator**：量比指标

## 数据字段标准

### 基础DataFrame字段
```
stock_code   # 股票代码
datetime     # 时间戳
trade_date   # 交易日期（YYYY-MM-DD）
open         # 开盘价
close        # 收盘价
high         # 最高价
low          # 最低价
volume       # 成交量
amount       # 成交额
```

### 指标DataFrame字段（示例KDJ）
```
基础字段 + kdj_k, kdj_d, kdj_j
```

## 项目结构

```
pystock_data/
├── source/           # 数据源层
│   ├── tdx_source.py # 通达信数据源
│   └── utils.py      # 工具函数
│
├── basic/            # 基础数据层
│   ├── bars.py       # K线数据
│   └── minutes.py    # 分时数据
│
├── indicators/       # 指标数据层
│   ├── base.py       # 指标基类
│   ├── kdj.py        # KDJ指标
│   ├── macd.py       # MACD指标
│   ├── ma.py         # 均线指标
│   └── volume_ratio.py # 量比指标
│
└── tests/            # 测试模块
```

## 文档

### 核心文档
- [API使用指南](docs/api_usage_guide.md) - **完整API调用示例**（推荐先阅读）
- [项目规范文档](PROJECT_STANDARDS.md)
- [架构设计文档](docs/architecture.md)
- [命名规范指南](docs/naming_guide.md)
- [代码风格指南](docs/code_style.md)

### 快速理解项目
1. 阅读 [API使用指南](docs/api_usage_guide.md) 了解如何调用
2. 查看 [examples/](examples/) 目录的示例代码
3. 参考 [architecture.md](docs/architecture.md) 了解架构设计

## 贡献指南

请遵循项目规范文档进行开发和提交。

## 许可证

MIT License