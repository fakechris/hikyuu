# PyBacktest

PyBacktest是一个纯Python实现的回测引擎，用于量化交易策略的回测和分析。它提供了灵活的架构，允许用户自定义交易策略、信号生成器和资金管理规则。

## 目录

- [设计文档](#设计文档)
  - [项目概述](#项目概述)
  - [架构设计](#架构设计)
  - [核心组件](#核心组件)
- [功能说明](#功能说明)
  - [数据管理](#数据管理)
  - [交易管理](#交易管理)
  - [信号生成](#信号生成)
  - [策略实现](#策略实现)
  - [回测执行](#回测执行)
  - [绩效分析](#绩效分析)
- [安装与依赖](#安装与依赖)
- [快速开始](#快速开始)
- [示例](#示例)
- [扩展指南](#扩展指南)
- [未来计划](#未来计划)
- [许可证](#许可证)

## 设计文档

### 项目概述

PyBacktest是一个轻量级的量化交易回测框架，完全使用Python实现，不依赖任何C++库。它的设计理念借鉴了Hikyuu等成熟回测系统，但更加注重简洁性和可扩展性。

项目目标：
- 提供一个易于理解和使用的回测框架
- 支持多种交易策略和信号生成方法
- 提供详细的绩效分析和可视化功能
- 保持代码的模块化和可扩展性

### 架构设计

PyBacktest采用模块化设计，主要包含以下几个模块：

1. **数据模块**：负责加载和处理历史数据
2. **交易模块**：负责模拟交易操作和资金管理
3. **信号模块**：负责生成交易信号
4. **策略模块**：负责实现交易策略
5. **回测模块**：负责执行回测流程
6. **绩效模块**：负责分析回测结果

这些模块之间的关系如下：

```
数据模块 --> 信号模块 --> 策略模块 --> 回测模块 --> 绩效模块
                                ^
                                |
                          交易模块 ----+
```

### 核心组件

PyBacktest的核心组件包括：

1. **DataHandler**：数据处理类，负责加载和管理历史数据
2. **TradeManager**：交易管理类，负责管理交易记录和资金
3. **SignalGenerator**：信号生成器基类，派生出多种具体的信号生成器
4. **Strategy**：策略基类，派生出多种具体的策略实现
5. **Backtest**：回测引擎类，负责执行回测
6. **Performance**：绩效分析类，负责计算和分析回测结果

## 功能说明

### 数据管理

`DataHandler`类提供了以下功能：

- 从CSV文件加载数据
- 从DataFrame加载数据
- 自动计算常用技术指标（移动平均线、MACD、RSI等）
- 按日期范围筛选数据
- 生成交易信号

```python
# 创建数据处理器
data_handler = DataHandler()

# 从CSV文件加载数据
data_handler.load_csv('AAPL', 'apple_stock_data.csv')

# 从DataFrame加载数据
data_handler.load_dataframe('MSFT', df)

# 获取数据
data = data_handler.get_data('AAPL', start_date='2020-01-01', end_date='2020-12-31')
```

### 交易管理

`TradeManager`类提供了以下功能：

- 模拟买入和卖出操作
- 计算交易成本（佣金和滑点）
- 管理持仓和资金
- 记录交易历史
- 计算投资组合价值

```python
# 创建交易成本对象
trade_cost = TradeCost(commission_rate=0.0003, min_commission=5.0, slippage_rate=0.0001)

# 创建交易管理器
trade_manager = TradeManager(initial_cash=100000.0, trade_cost=trade_cost)

# 买入操作
trade_manager.buy(date=datetime.now(), symbol='AAPL', price=150.0, shares=100)

# 卖出操作
trade_manager.sell(date=datetime.now(), symbol='AAPL', price=160.0, shares=100)

# 获取持仓
position = trade_manager.get_position('AAPL')

# 获取交易历史
trade_history = trade_manager.get_trade_history()
```

### 信号生成

PyBacktest提供了多种信号生成器：

- **CrossSignal**：均线交叉信号
- **MACDSignal**：MACD信号
- **RSISignal**：RSI信号
- **BreakoutSignal**：突破信号
- **CompositeSignal**：组合信号

```python
# 创建均线交叉信号生成器
cross_signal = CrossSignal(fast_ma='ma5', slow_ma='ma20')

# 创建MACD信号生成器
macd_signal = MACDSignal()

# 创建RSI信号生成器
rsi_signal = RSISignal(overbought=70, oversold=30)

# 创建组合信号生成器
composite_signal = CompositeSignal(
    signal_generators=[cross_signal, macd_signal, rsi_signal],
    weights=[0.5, 0.3, 0.2]
)
```

### 策略实现

PyBacktest提供了多种策略类：

- **SignalStrategy**：基于单一信号的策略
- **MultiSignalStrategy**：基于多信号的策略
- **PortfolioStrategy**：投资组合策略

```python
# 创建基于信号的策略
strategy = SignalStrategy(cross_signal, 'AAPL')

# 创建多信号策略
multi_strategy = MultiSignalStrategy(
    signal_generators=[cross_signal, macd_signal, rsi_signal],
    symbol='AAPL',
    weights=[0.5, 0.3, 0.2]
)

# 创建投资组合策略
portfolio_strategy = PortfolioStrategy({
    'AAPL': SignalStrategy(cross_signal, 'AAPL'),
    'MSFT': SignalStrategy(macd_signal, 'MSFT')
})
```

### 回测执行

`Backtest`类负责执行回测，并提供绩效分析和可视化功能：

```python
# 创建回测引擎
backtest = Backtest(data_handler, trade_manager)

# 运行单一策略回测
result = backtest.run(strategy, 'AAPL', position_pct=0.9)

# 运行投资组合回测
results = backtest.run_portfolio(portfolio_strategy, data_dict, position_pct={'AAPL': 0.6, 'MSFT': 0.4})

# 获取绩效统计
stats = backtest.get_performance()

# 绘制权益曲线
backtest.plot_equity_curve()

# 绘制回撤曲线
backtest.plot_drawdown()

# 绘制月度收益热图
backtest.plot_monthly_returns()

# 绘制交易点位
backtest.plot_trades('AAPL')

# 保存回测结果
backtest.save_results('backtest_results.xlsx')
```

### 绩效分析

`Performance`类提供了详细的绩效统计和分析：

```python
# 获取绩效统计
stats = backtest.performance.get_stats()

# 打印绩效报告
backtest.performance.print_report()

# 绘制权益曲线
backtest.performance.plot_equity_curve()

# 绘制回撤曲线
backtest.performance.plot_drawdown()

# 绘制月度收益热图
backtest.performance.plot_monthly_returns()
```

主要绩效指标包括：

- 总收益率和年化收益率
- 最大回撤
- 夏普比率
- 胜率和盈亏比
- 平均盈利和亏损
- 平均持仓天数
- 等等

## 安装与依赖

PyBacktest依赖以下Python库：

- pandas
- numpy
- matplotlib
- seaborn

安装依赖：

```bash
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

## 示例

查看`example.py`文件，了解如何使用PyBacktest进行回测。该示例展示了：

1. 创建示例数据
2. 使用均线交叉策略进行回测
3. 使用多信号策略进行回测
4. 绘制权益曲线和交易点位
5. 保存回测结果

## 扩展指南

PyBacktest的模块化设计使其易于扩展。以下是一些扩展示例：

### 创建自定义信号生成器

```python
from pybacktest import SignalGenerator

class MySignalGenerator(SignalGenerator):
    def __init__(self, param1, param2, name="MySignal"):
        super().__init__(name)
        self.param1 = param1
        self.param2 = param2
    
    def generate(self, data):
        df = data.copy()
        # 实现信号生成逻辑
        df['signal'] = 0
        # ...
        return df
```

### 创建自定义策略

```python
from pybacktest import Strategy

class MyStrategy(Strategy):
    def __init__(self, param1, param2, name="MyStrategy"):
        super().__init__(name)
        self.param1 = param1
        self.param2 = param2
    
    def generate_signals(self, data):
        df = data.copy()
        # 实现信号生成逻辑
        df['signal'] = 0
        # ...
        return df
    
    def run(self, data, trade_manager, **kwargs):
        # 实现策略运行逻辑
        # ...
        return result_df
```

## 未来计划

PyBacktest仍在积极开发中，以下是未来计划的功能：

1. **事件驱动模式**：实现事件驱动的回测模式，以支持实盘交易
2. **更多信号生成器**：添加更多的技术指标和信号生成方法
3. **风险管理**：添加更完善的风险管理功能
4. **性能优化**：优化代码性能，支持大规模回测
5. **机器学习集成**：添加机器学习模型的集成功能
6. **回测报告**：生成更详细的回测报告和可视化
7. **实盘接口**：添加与实盘交易系统的接口
8. **并行计算**：支持多进程并行回测
9. **因子分析**：添加因子分析功能
10. **优化工具**：添加参数优化和遗传算法优化工具

## 许可证

MIT

---

© 2023 PyBacktest Team. 保留所有权利。
