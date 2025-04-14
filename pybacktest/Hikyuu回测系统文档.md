# Hikyuu回测系统文档

## 1. 回测系统概述

Hikyuu Quant Framework是一款基于C++/Python的开源量化交易研究框架，用于策略分析及回测。其核心思想基于当前成熟的系统化交易方法，将整个系统化交易抽象为由七大组件构成：

- 市场环境判断策略
- 系统有效条件
- 信号指示器
- 止损/止盈策略
- 资金管理策略
- 盈利目标策略
- 移滑价差算法

Hikyuu的回测系统设计灵活，允许用户自由组合这些组件，以评估交易系统的有效性、稳定性以及单一种类策略的效果。

## 2. 回测核心组件

### 2.1 TradeManager（交易管理器）

TradeManager是回测系统的核心组件之一，负责管理账户的交易记录及资金使用情况。它模拟了一个交易账户，记录买入、卖出等交易操作，并计算账户的资金状况。

```python
# 创建交易管理器示例
my_tm = crtTM(
    date=Datetime(201701010000),  # 账户建立日期
    init_cash=300000,             # 初始资金
    cost_func=TC_Zero(),          # 交易成本算法
    name="SYS"                    # 账户名称
)
```

主要功能：
- 记录交易操作（买入、卖出、分红等）
- 管理账户资金
- 计算持仓情况
- 支持融资融券
- 计算交易成本

### 2.2 System（交易系统）

System是交易系统的核心，它整合了各个交易组件，并提供了运行回测的接口。System类是所有交易系统的基类，用户可以通过继承该类来实现自定义的交易系统。

```python
# 创建简单交易系统示例
sys = SYS_Simple(
    tm=my_tm,                 # 交易管理器
    mm=my_mm,                 # 资金管理策略
    sg=my_sg,                 # 信号指示器
    st=my_st,                 # 止损策略
    tp=my_tp,                 # 止盈策略
    pg=my_pg,                 # 盈利目标策略
    sp=my_sp                  # 移滑价差算法
)
```

主要功能：
- 整合各个交易组件
- 运行回测
- 生成交易信号
- 执行交易操作
- 记录交易结果

### 2.3 Portfolio（投资组合）

Portfolio实现了多标的、多策略的投资组合管理。它可以同时运行多个交易系统，并根据资产分配算法在不同的交易系统之间分配资金。

```python
# 创建投资组合示例
my_pf = PF_Simple(
    tm=my_tm,     # 交易管理器
    af=my_af,     # 资产分配算法
    se=my_se      # 选择器
)
```

主要功能：
- 管理多个交易系统
- 在不同交易系统之间分配资金
- 运行投资组合回测
- 评估投资组合绩效

### 2.4 其他核心组件

#### 2.4.1 信号指示器（Signal）

信号指示器负责生成买入和卖出信号，是交易系统的核心组件之一。

```python
# 创建信号指示器示例
my_sg = SG_Flex(EMA(CLOSE(), n=5), slow_n=10)
```

#### 2.4.2 资金管理策略（MoneyManager）

资金管理策略决定每次交易的资金量或股票数量。

```python
# 创建资金管理策略示例
my_mm = MM_FixedCount(1000)  # 固定每次买入1000股
```

#### 2.4.3 止损策略（Stoploss）

止损策略用于控制风险，当价格达到止损条件时触发卖出操作。

```python
# 创建止损策略示例
my_st = ST_FixedPercent(0.05)  # 固定5%止损
```

#### 2.4.4 止盈策略（ProfitGoal）

止盈策略用于锁定利润，当价格达到止盈条件时触发卖出操作。

```python
# 创建止盈策略示例
my_tp = ST_Indicator(MA(CLOSE(), 5))  # 当价格低于5日均线时止盈
```

#### 2.4.5 移滑价差算法（Slippage）

移滑价差算法用于模拟实际交易中的滑点影响。

```python
# 创建移滑价差算法示例
my_sp = SP_FixedPercent(0.001)  # 固定0.1%的滑点
```

## 3. 回测流程

### 3.1 基本回测流程

Hikyuu的回测流程主要包括以下步骤：

1. **创建交易管理器**：设置初始资金、交易成本等参数
2. **创建交易组件**：创建信号指示器、资金管理策略等组件
3. **创建交易系统**：整合各个交易组件
4. **运行回测**：指定股票和时间范围，运行回测
5. **分析结果**：分析回测结果，评估策略绩效

```python
# 基本回测流程示例
# 1. 创建交易管理器
my_tm = crtTM(init_cash=300000)

# 2. 创建交易组件
my_sg = SG_Flex(EMA(CLOSE(), n=5), slow_n=10)  # 信号指示器
my_mm = MM_FixedCount(1000)                    # 资金管理策略

# 3. 创建交易系统
sys = SYS_Simple(tm=my_tm, sg=my_sg, mm=my_mm)

# 4. 运行回测
sys.run(sm['sz000001'], Query(-150))

# 5. 分析结果
per = Performance()
print(per.report(my_tm))
```

### 3.2 回测与实盘的区别

Hikyuu的回测流程与实盘交易有显著不同，主要采用批量处理方式：

1. **数据加载**：
   - 加载指定时间范围内的所有K线数据
   - 一次性将数据传递给策略

2. **信号生成**：
   - 信号生成器的`_calculate`方法被调用一次
   - 在方法内部遍历所有K线数据，生成买卖信号

3. **交易模拟**：
   - 根据生成的信号模拟交易执行
   - 计算交易结果和绩效指标

而实盘交易则是事件驱动的，通过回调函数处理市场数据和交易信号。

### 3.3 投资组合回测

投资组合回测允许同时测试多个股票和多个策略的组合效果：

```python
# 创建一个系统策略
my_mm = MM_FixedCount(100)
my_sg = SG_Flex(EMA(n=5), slow_n=10)
my_sys = SYS_Simple(sg=my_sg, mm=my_mm)

# 创建一个选择算法，用于在每日选定交易系统
my_se = SE_Fixed([s for s in blocka if s.valid], my_sys)

# 创建一个资产分配器
my_af = AF_EqualWeight()

# 创建资产组合
my_tm = crtTM(Datetime(200101010000), 2000000)
my_pf = PF_Simple(tm=my_tm, af=my_af, se=my_se)

# 运行投资组合
my_pf.run(Query(-500))
```

## 4. 回测结果分析

### 4.1 Performance类

Performance类提供了丰富的绩效统计指标，用于评估交易系统的性能。

```python
# 使用Performance类分析回测结果
per = Performance()
per.statistics(my_tm)  # 统计绩效
print(per.report(my_tm))  # 打印报告
```

主要统计指标包括：

- 账户初始金额
- 累计投入本金
- 当前总资产
- 已平仓净利润总额
- 赢利交易比例
- 赢利交易平均赢利
- 亏损交易平均亏损
- 最大单笔赢利/亏损
- 最大连续赢利/亏损笔数
- 年化收益率
- 交易机会频率
- R乘数期望值
- 等等

### 4.2 可视化分析

Hikyuu提供了多种可视化工具，用于直观地分析回测结果：

```python
# 绘制系统实际买入/卖出信号
sysplot(sys)

# 绘制系统绩效（账户累积收益率曲线）
sys_performance(sys)

# 绘制系统收益年-月收益热力图
sys_heatmap(sys)
```

### 4.3 交易记录分析

可以通过TradeManager获取交易记录，并进行详细分析：

```python
# 获取交易记录
trade_list = my_tm.get_trade_list()
for trade in trade_list:
    print(trade)

# 导出交易记录到CSV
my_tm.tocsv("./backtest_results")
```

## 5. 回测优化方法

### 5.1 参数优化

可以通过遍历不同的参数组合，找到最优的参数设置：

```python
# 参数优化示例
best_params = None
best_performance = 0

for n1 in range(5, 20, 5):
    for n2 in range(10, 30, 5):
        my_sg = SG_Flex(EMA(CLOSE(), n=n1), slow_n=n2)
        sys = SYS_Simple(tm=my_tm, sg=my_sg, mm=my_mm)
        sys.run(sm['sz000001'], Query(-150))
        
        per = Performance()
        per.statistics(my_tm)
        performance = per.get("帐户平均年收益率%")
        
        if performance > best_performance:
            best_performance = performance
            best_params = (n1, n2)

print(f"最优参数: {best_params}, 年收益率: {best_performance}%")
```

### 5.2 多策略组合

通过组合多个策略，可以降低单一策略的风险：

```python
# 多策略组合示例
my_sg1 = SG_Flex(EMA(CLOSE(), n=5), slow_n=10)
my_sg2 = SG_Cross(MA(CLOSE(), 5), MA(CLOSE(), 10))

sys1 = SYS_Simple(tm=my_tm, sg=my_sg1, mm=my_mm)
sys2 = SYS_Simple(tm=my_tm, sg=my_sg2, mm=my_mm)

# 使用选择器组合策略
my_se = SE_Fixed([sys1, sys2])

# 使用资产分配器分配资金
my_af = AF_EqualWeight()

# 创建投资组合
my_pf = PF_Simple(tm=my_tm, af=my_af, se=my_se)
my_pf.run(Query(-500))
```

### 5.3 使用寻优选择器

Hikyuu提供了寻优选择器，可以自动选择最优的交易系统：

```python
# 使用寻优选择器示例
my_se = SE_PerformanceOptimal(key="帐户平均年收益率%", mode=0)
my_pf = PF_Simple(tm=my_tm, af=my_af, se=my_se)
my_pf.run(Query(-500))
```

## 6. 实例演示

### 6.1 简单均线交叉策略回测

```python
# 创建交易管理器
my_tm = crtTM(init_cash=300000)

# 创建信号指示器（5日均线上穿10日均线买入，下穿卖出）
my_sg = SG_Cross(MA(CLOSE(), 5), MA(CLOSE(), 10))

# 固定每次买入1000股
my_mm = MM_FixedCount(1000)

# 创建交易系统并运行
sys = SYS_Simple(tm=my_tm, sg=my_sg, mm=my_mm)
sys.run(sm['sz000001'], Query(-150))

# 分析结果
per = Performance()
print(per.report(my_tm))

# 可视化分析
sysplot(sys)
sys_performance(sys)
```

### 6.2 带止损止盈的策略回测

```python
# 创建交易管理器
my_tm = crtTM(init_cash=300000)

# 创建信号指示器
my_sg = SG_Flex(EMA(CLOSE(), n=5), slow_n=10)

# 固定每次买入1000股
my_mm = MM_FixedCount(1000)

# 创建止损策略（固定5%止损）
my_st = ST_FixedPercent(0.05)

# 创建止盈策略（当价格低于5日均线时止盈）
my_tp = ST_Indicator(MA(CLOSE(), 5))

# 创建交易系统并运行
sys = SYS_Simple(tm=my_tm, sg=my_sg, mm=my_mm, st=my_st, tp=my_tp)
sys.run(sm['sz000001'], Query(-150))

# 分析结果
per = Performance()
print(per.report(my_tm))
```

### 6.3 多股票投资组合回测

```python
# 创建交易管理器
my_tm = crtTM(init_cash=1000000)

# 创建信号指示器
my_sg = SG_Flex(EMA(CLOSE(), n=5), slow_n=10)

# 创建资金管理策略（每次使用10%的资金）
my_mm = MM_FixedPercent(0.1)

# 创建交易系统
my_sys = SYS_Simple(sg=my_sg, mm=my_mm)

# 创建股票池
stocks = [sm['sz000001'], sm['sh600000'], sm['sh601318']]

# 创建选择器
my_se = SE_Fixed(stocks, my_sys)

# 创建资产分配器
my_af = AF_EqualWeight()

# 创建投资组合
my_pf = PF_Simple(tm=my_tm, af=my_af, se=my_se)

# 运行投资组合
my_pf.run(Query(-500))

# 分析结果
per = Performance()
print(per.report(my_tm))
```

## 7. 总结

Hikyuu提供了一个灵活、强大的回测框架，允许用户自由组合各种交易组件，以评估交易系统的有效性。通过本文档，我们介绍了Hikyuu回测系统的核心组件、回测流程、结果分析和优化方法，并提供了多个实例演示。

使用Hikyuu进行回测时，需要注意以下几点：

1. 合理设置初始资金和交易成本，以模拟真实交易环境
2. 考虑滑点影响，使回测结果更接近实际交易
3. 使用止损策略控制风险
4. 通过参数优化和多策略组合提高策略稳定性
5. 全面分析回测结果，不仅关注收益率，还要关注风险指标

通过这些方法，可以开发出更加稳健的交易策略，提高投资决策的质量。
