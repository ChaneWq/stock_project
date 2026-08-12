# PyStock 示例代码

本目录包含 PyStock 数据层的使用示例，帮助开发者快速上手。

## 文档导航

### API使用指南
完整的API调用示例和说明文档：
- [docs/api_usage_guide.md](../docs/api_usage_guide.md) - **完整API使用指南**
  - 包含所有模块的详细调用示例
  - 完整的应用场景演示
  - 错误处理和性能优化建议
  - API速查表和最佳实践

**快速理解项目：建议先阅读API使用指南**

## 示例文件

### quick_test.py
快速功能演示脚本，展示数据层的核心功能：
- 基础K线数据获取（日线、周线、月线）
- 基础分时数据获取
- KDJ指标计算
- MACD指标计算
- 均线指标计算
- 多指标组合使用

运行方式：
```bash
python examples/quick_test.py
```

### ma_dynamic_params_demo.py
MA指标动态参数功能演示：
- 默认周期使用：`[5, 10, 20, 60]`
- 初始化自定义周期：`MAIndicator(periods=[3, 5, 7])`
- 运行时动态传入周期：`ma.calculate(df, periods=[10, 20, 30])`
- 不同策略使用不同周期组合（短线、中线、长线）
- 参数验证错误案例展示

运行方式：
```bash
python examples/ma_dynamic_params_demo.py
```

关键特性：
- **灵活性**：一个实例多次使用不同参数
- **向后兼容**：现有代码无需修改
- **参数验证**：自动检查参数合法性

### basic_minutes_with_vr_demo.py ✨新增
分时量比完整演示，展示BasicMinutesWithVR的全部功能：
- **基本使用**：获取带量比的分时数据（自动计算量比）
- **量比分析**：统计摘要、趋势判断、含义分析
- **量比过滤**：放量时段、缩量时段、峰值查找
- **对比分析**：BasicMinutes vs BasicMinutesWithVR
- **批量分析**：多股票量比对比、活跃度排序
- **时段分析**：开盘、盘中、收盘时段量比特征
- **应用场景**：异常放量监控、缩量预警、活跃时段筛选

运行方式：
```bash
python examples/basic_minutes_with_vr_demo.py
```

关键特性：
- **自动计算**：自动获取过去n日数据计算量比
- **正确公式**：量比 = 累计成交量 / 时间序号 / 过去n日分钟均量
- **完整功能**：统计、过滤、趋势、峰值查找等
- **实战应用**：异常监控、时段分析、批量对比

量比含义：
- `>3`：明显放量（异常活跃）
- `2~3`：放量（活跃）
- `1~2`：正常
- `0.5~1`：缩量（清淡）
- `<0.5`：明显缩量（异常清淡）

## 使用示例

### MA指标三种使用方式

```python
from pystock_data.basic import BasicBars
from pystock_data.indicators import MAIndicator

bars = BasicBars()
basic_df = bars.get_daily('000400', 100)

# 方式1：默认周期
ma = MAIndicator()
df1 = ma.calculate(basic_df)  # 使用[5, 10, 20, 60]

# 方式2：初始化自定义周期
ma = MAIndicator(periods=[3, 5, 7])
df2 = ma.calculate(basic_df)  # 使用[3, 5, 7]

# 方式3：运行时动态传入周期
ma = MAIndicator()  # 默认[5, 10, 20, 60]
df3 = ma.calculate(basic_df, periods=[10, 20, 30])  # 临时使用[10, 20, 30]
df4 = ma.calculate(basic_df)  # 仍使用默认[5, 10, 20, 60]
```

## 更多示例

待添加：
- 实战策略示例
- 数据分析示例
- 可视化示例

## 使用建议

1. 先运行 `quick_test.py` 验证安装是否正常
2. 运行 `ma_dynamic_params_demo.py` 了解MA指标动态参数功能
3. 运行 `basic_minutes_with_vr_demo.py` 了解分时量比完整功能 ✨
4. 查看示例代码了解 API 使用方法
5. 根据需要修改示例代码进行测试
6. 参考示例开发自己的应用