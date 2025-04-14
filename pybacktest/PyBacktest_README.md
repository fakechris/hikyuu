# PyBacktest

PyBacktest是一个纯Python实现的回测引擎，用于量化交易策略的回测和分析。它提供了灵活的架构，允许用户自定义交易策略、信号生成器和资金管理规则。

## 特点

- 纯Python实现，无需额外依赖C++库
- 模块化设计，易于扩展
- 支持多种交易信号生成器
- 支持单一策略和多策略组合
- 详细的绩效分析和可视化
- 支持交易成本和滑点模拟
- 支持投资组合回测

## 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/pybacktest.git
cd pybacktest

# 安装依赖
pip install pandas numpy matplotlib seaborn
```

## 快速开始

以下是一个简单的回测示例：

```python
import pandas as pd
from pybacktest import (
    DataHandler, TradeManager, CrossSignal,
    SignalStrategy, Backtest
)

# 创建数据处理器
data_handler = DataHandler()

# 加载数据
data = pd.read_csv('stock_data.csv')
data['date'] = pd.to_datetime(data['date'])
data.set_index('date', inplace=True)
data_handler.load_dataframe('AAPL', data)

# 创建交易管理器
trade_manager = TradeManager(initial_cash=100000.0)

# 创建信号生成器
cross_signal = CrossSignal(fast_ma='ma5', slow_ma='ma20')

# 创建策略
strategy = SignalStrategy(cross_signal, 'AAPL')

# 创建回测引擎
backtest = Backtest(data_handler, trade_manager)

# 运行回测
result = backtest.run(strategy, 'AAPL', position_pct=0.9)

# 打印绩效报告
backtest.performance.print_report()

# 绘制权益曲线
backtest.plot_equity_curve()

# 绘制交易点位
backtest.plot_trades('AAPL')
```

## 核心组件

### 数据管理

`DataHandler`类负责加载和处理历史数据，支持从CSV文件或DataFrame加载数据，并自动计算常用技术指标。

### 交易管理

`TradeManager`类负责管理交易记录和资金，模拟买入和卖出操作，并计算交易成本。

### 信号生成

提供多种信号生成器，包括：
- `CrossSignal`：均线交叉信号
- `MACDSignal`：MACD信号
- `RSISignal`：RSI信号
- `BreakoutSignal`：突破信号
- `CompositeSignal`：组合信号

### 策略

提供多种策略类，包括：
- `SignalStrategy`：基于单一信号的策略
- `MultiSignalStrategy`：基于多信号的策略
- `PortfolioStrategy`：投资组合策略

### 回测引擎

`Backtest`类负责执行回测，并提供绩效分析和可视化功能。

### 绩效分析

`Performance`类提供详细的绩效统计和分析，包括：
- 总收益率和年化收益率
- 最大回撤
- 夏普比率
- 胜率和盈亏比
- 平均盈利和亏损
- 等等

## 示例

查看`example.py`文件，了解如何使用PyBacktest进行回测。

## 扩展

PyBacktest的模块化设计使其易于扩展。您可以：
- 创建自定义信号生成器
- 实现自定义策略
- 添加新的绩效指标
- 扩展可视化功能

## 许可证

MIT
