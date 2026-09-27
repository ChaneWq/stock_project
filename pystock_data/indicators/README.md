# 指标库说明

指标实现位于本目录，统一从 `pystock_data.indicators` 导入。

## 使用方式

```python
from pystock_data.indicators import MAIndicator

ma = MAIndicator()
df = ma.calculate(basic_df)  # 输入DataFrame，返回 原字段 + 指标字段
```

## 指标清单

| 指标类 | 说明 | 默认参数 | 输出字段 | 所需字段 |
|---|---|---|---|---|
| `MAIndicator` | 移动平均线 | periods=[5,10,20,60] | ma5 / ma10 / ma20 / ma60 | close |
| `MACDIndicator` | MACD | 12/26/9 | macd_dif / macd_dea / macd_macd | close |
| `KDJIndicator` | KDJ 随机指标 | n=9, m1=3, m2=3 | kdj_k / kdj_d / kdj_j | high, low, close |
| `BBIIndicator` | BBI 多空均线 | 3/6/12/24 | bbi | close |
| `VolumeMAIndicator` | 成交量均线 | periods=[5] | vma5（可扩展） | volume |
| `VWAPIndicator` | 分时均价线（黄线） | 无 | avg_price | volume + close（或 price），需分时数据 |
| `ZXShortTermTrendIndicator` | ZX 短线趋势（双层EMA） | n=10 | zx_short_term_trend | close |
| `ZXBullBearLineIndicator` | ZX 牛熊分界线 | 3/6/12/24 | zx_bull_bear_line | close |
| `ZXTIndicator` | ZXT 砖型图强度 | n=4, m1=4, m2=6 | zxt | high, low, close |
| `DZSIndicator` | 3日单针（区间百分位） | period=3 | dzs | high, low, close |
| `DZTIndicator` | 21日单针（区间百分位） | period=21 | dzt | high, low, close |

## 测试 Demo

位于 `pystock_data/demo/indicators/`：

| 文件 | 内容 |
|---|---|
| `vma_demo.py` | 成交量均线验证（真实日线 + 手工核对） |
| `vwap_demo.py` | 分时均价线验证（真实分时 + 手工核算） |

运行方式（项目根目录下）：

```bash
python -m pystock_data.demo.indicators.vma_demo
python -m pystock_data.demo.indicators.vwap_demo
```
