# Hikyuu引擎流程文档

## 目录
1. [引擎回调流程](#引擎回调流程)
2. [事件处理流程](#事件处理流程)
3. [回测流程](#回测流程)
4. [实盘与回测的区别](#实盘与回测的区别)
5. [源码解析](#源码解析)
6. [复杂交易场景模拟](#复杂交易场景模拟)

## 引擎回调流程

Hikyuu引擎在实盘交易中采用事件驱动模型，通过一系列回调函数处理市场数据和交易信号。以下是核心回调流程：

### 初始化阶段

```python
# 创建策略实例
s = Strategy(['sh600000', 'sz000001'], [Query.MIN, Query.DAY])

# 注册回调函数
s.on_change(on_change)
s.on_received_spot(on_spot)

# 注册定时任务
s.run_daily(my_func, TimeDelta(minutes=5))
s.run_daily_at(my_func, Datetime.now() + Seconds(10), False)
```

### 数据接收与处理流程

1. **行情数据接收**：
   - 行情数据通过行情接口（如HikyuuTdx）接收
   - 数据被包装成`SpotRecord`对象

2. **回调触发顺序**：
   - 当接收到新行情时，首先触发`on_received_spot`回调
   - 然后，对每只有新数据的股票，触发`on_change`回调
   - 定时任务根据设定的时间触发

### 源码实现

在`Strategy.cpp`中，回调函数的注册和触发流程如下：

```cpp
// 注册股票行情变化回调
void Strategy::onChange(std::function<void(const Stock&, const SpotRecord& spot)>&& changeFunc) {
    HKU_CHECK(changeFunc, "Invalid changeFunc!");
    m_on_change = std::move(changeFunc);
}

// 注册行情接收回调
void Strategy::onReceivedSpot(std::function<void(const Datetime&)>&& recievedFucn) {
    HKU_CHECK(recievedFucn, "Invalid recievedFucn!");
    m_on_recieved_spot = std::move(recievedFucn);
}

// 行情数据接收处理
void Strategy::_receivedSpot(const SpotRecord& spot) {
    Stock stk = getStock(format("{}{}", spot.market, spot.code));
    if (!stk.isNull()) {
        if (m_on_change) {
            event([this, stk, spot]() { m_on_change(stk, spot); });
        }
    }
}
```

## 事件处理流程

Hikyuu采用事件队列机制处理各种事件，确保事件按顺序处理并避免并发问题。

### 事件队列机制

1. **事件入队**：
   - 通过`event()`函数将事件（回调函数）加入队列
   - 事件队列在主线程中处理，避免Python GIL问题

2. **事件循环**：
   - 在`_startEventLoop()`方法中实现
   - 循环处理队列中的事件，直到策略停止运行

### 源码实现

```cpp
// 在主线程中处理事件队列，避免 python GIL
void Strategy::_startEventLoop() {
    while (ms_keep_running) {
        std::function<void()> func;
        {
            std::unique_lock<std::mutex> lock(m_event_mutex);
            if (m_event_queue.empty()) {
                m_event_cond.wait_for(lock, std::chrono::milliseconds(100));
                continue;
            }
            func = std::move(m_event_queue.front());
            m_event_queue.pop();
        }
        if (func) {
            func();
        }
    }
}
```

## 回测流程

Hikyuu的回测流程与实盘交易有显著不同，主要采用批量处理方式。

### 回测初始化

```python
# 创建交易系统
my_sys = System(tm, mm, ev)
my_sys.sg = my_sg  # 设置信号生成器

# 设置回测区间
start_date = Datetime(202301010000)
end_date = Datetime(202412310000)
query = Query(start_date, end_date, ktype=Query.DAY)
```

### 回测执行流程

1. **数据加载**：
   - 加载指定时间范围内的所有K线数据
   - 一次性将数据传递给策略

2. **信号生成**：
   - 信号生成器的`_calculate`方法被调用一次
   - 在方法内部遍历所有K线数据，生成买卖信号

3. **交易模拟**：
   - 根据生成的信号模拟交易执行
   - 计算交易结果和绩效指标

### 源码实现

在`RunSystemInStrategy.cpp`中，回测执行的核心逻辑如下：

```cpp
void RunSystemInStrategy::run(const Stock& stock) {
    // 处理延迟买入请求
    if (m_sys->getParam<bool>("buy_delay") && m_buyRequest.valid) {
        // 执行买入操作
    }

    // 处理延迟卖出请求
    if (m_sys->getParam<bool>("sell_delay") && m_sellRequest.valid) {
        // 执行卖出操作
    }

    // 从经纪人获取资产信息
    m_sys->getTM()->fetchAssetInfoFromBroker(m_broker);

    // 设置系统的股票和查询条件
    m_sys->setStock(stock);
    KData k = stock.getKData(m_query);
    if (k.empty()) {
        return;
    }

    // 运行系统
    m_sys->run(k, m_query.start(), Null<size_t>());
}
```

## 实盘与回测的区别

### 数据处理方式

| 特性 | 回测模式 | 实盘模式 |
|------|---------|---------|
| 数据加载 | 一次性加载所有历史数据 | 实时接收市场数据 |
| 处理方式 | 批量处理所有K线 | 逐个处理每条行情 |
| 信号生成 | 在`_calculate`中一次性生成所有信号 | 在`on_change`回调中实时生成信号 |

### 执行流程差异

1. **回测模式**：
   - 系统调用`run`方法一次
   - `_calculate`方法处理整个数据序列
   - 模拟交易执行和结果计算

2. **实盘模式**：
   - 系统启动后进入事件循环
   - 通过回调函数处理实时数据
   - 实时生成交易信号并执行

## 源码解析

### 策略初始化 (Strategy.cpp)

```cpp
Strategy::Strategy(const vector<string>& codeList, const vector<KQuery::KType>& ktypeList,
                   const string& name, const string& config_file)
: m_name(name), m_config_file(config_file) {
    _initParam();
    
    // 初始化股票列表和K线类型
    for (const auto& code : codeList) {
        auto pos = code.find(":");
        if (pos != string::npos) {
            m_stk_list.push_back(code);
        } else {
            m_stk_list.push_back(code);
        }
    }
    
    for (auto ktype : ktypeList) {
        m_ktype_list.push_back(ktype);
    }
}
```

### 事件处理 (Strategy.cpp)

```cpp
void Strategy::event(std::function<void()>&& func) {
    std::unique_lock<std::mutex> lock(m_event_mutex);
    m_event_queue.push(std::move(func));
    m_event_cond.notify_one();
}
```

### 回测执行 (RunSystemInStrategy.cpp)

```cpp
StrategyPtr crtSysStrategy(const SYSPtr& sys, const string& stk_market_code, const KQuery& query,
                           const OrderBrokerPtr& broker, const TradeCostPtr& costfunc,
                           const string& name, const std::vector<OrderBrokerPtr>& other_brokers,
                           const string& config_file) {
    HKU_ASSERT(sys && broker);
    
    // 创建策略上下文
    StrategyContext context;
    context.stk_list = {stk_market_code};
    context.ktype_list = {query.kType()};
    
    // 创建策略
    auto strategy = make_shared<Strategy>(context, name, config_file);
    
    // 创建运行系统
    auto run_sys = make_shared<RunSystemInStrategy>(sys, broker, query, costfunc);
    
    // 注册回调函数
    strategy->onReceivedSpot([run_sys, stk_market_code](const Datetime&) {
        Stock stk = getStock(stk_market_code);
        if (!stk.isNull()) {
            run_sys->run(stk);
        }
    });
    
    return strategy;
}
```

## 复杂交易场景模拟

在量化交易系统中，真实市场的复杂性远超简单的买入卖出操作。Hikyuu提供了多种机制来模拟这些复杂交易场景，使回测结果更接近实际交易情况。

### 滑点模拟 (Slippage)

滑点是指实际成交价格与信号价格之间的差异，通常由市场流动性、交易延迟等因素导致。

#### 滑点模型类型

Hikyuu提供了多种滑点模型：

```python
# 固定滑点模型
sp_fixed = crtSP('FixedSlippage', {'value': 0.01})  # 固定0.01元滑点

# 百分比滑点模型
sp_percent = crtSP('PercentSlippage', {'p': 0.001})  # 0.1%的滑点

# 设置到系统中
my_sys.sp = sp_fixed
```

#### 滑点计算方式

- **买入时**：实际买入价格 = 信号价格 * (1 + 滑点)
- **卖出时**：实际卖出价格 = 信号价格 * (1 - 滑点)

#### 不同市场条件下的滑点设置

| 市场条件 | 建议滑点设置 | 原因 |
|---------|------------|------|
| 普通交易日 | 0.1% | 流动性正常 |
| 高波动期 | 0.3%-0.5% | 流动性下降，价格波动加大 |
| 首板/涨停板附近 | 0.5%-1% | 买盘拥挤，难以成交 |
| 小盘股 | 0.3%-0.5% | 流动性较差 |
| 大盘股 | 0.05%-0.1% | 流动性较好 |

### 交易成本 (TradeCost)

交易成本包括佣金、印花税、过户费等，会直接影响策略的盈利能力。

#### 交易成本模型

```python
# A股交易成本模型
tc = crtTC('A_Stock', {
    'commission': 0.0003,  # 佣金0.03%
    'stamptax': 0.001,     # 印花税0.1%
    'min_commission': 5.0  # 最低佣金5元
})

# 设置到交易管理器
my_tm = crtTM(init_cash=100000, tc=tc)
```

#### 交易成本计算

- **买入成本** = 买入金额 * 佣金率 (不低于最低佣金)
- **卖出成本** = 卖出金额 * 佣金率 (不低于最低佣金) + 卖出金额 * 印花税率

#### 不同券商和市场的交易成本

| 市场/券商类型 | 佣金率 | 印花税 | 其他费用 | 特点 |
|-------------|-------|-------|---------|------|
| A股普通券商 | 0.03% | 0.1% | 过户费等 | 最低佣金5元 |
| A股优惠券商 | 0.015%-0.025% | 0.1% | 过户费等 | 最低佣金2元 |
| 港股 | 0.1%-0.25% | 0.1% | 交易征费、交易费等 | 最低佣金较高 |
| 美股 | 固定费用/每股费用 | 无 | SEC费用等 | 不同券商差异大 |

### 交易成功率模拟

在实际交易中，并非所有订单都能成功执行，特别是在涨跌停板、流动性不足等情况下。

#### 订单代理模拟

```python
# 创建订单代理
broker = crtOB('OrderBrokerWrapper', {
    'buy_limit': 0.7,   # 买入成功率70%
    'sell_limit': 0.9,  # 卖出成功率90%
})

# 在系统中使用
my_sys.run(stock, query, broker)
```

#### 不同市场条件下的成功率设置

| 交易场景 | 买入成功率 | 卖出成功率 | 说明 |
|---------|----------|----------|------|
| 普通交易 | 90%-100% | 95%-100% | 流动性充足 |
| 涨停板买入 | 30%-50% | - | 买盘拥挤，成功率低 |
| 跌停板卖出 | - | 40%-60% | 卖盘拥挤，成功率低 |
| 小盘股交易 | 70%-80% | 80%-90% | 流动性较差 |
| 大单交易 | 60%-80% | 70%-90% | 市场冲击大 |

#### 自定义成功率模拟

对于更复杂的场景，可以自定义订单代理：

```python
class FirstBoardOrderBroker(OrderBrokerBase):
    def __init__(self):
        super(FirstBoardOrderBroker, self).__init__("FirstBoardOrderBroker")
        
    def _buy(self, datetime, market, code, price, num):
        # 获取当前K线数据
        stock = sm[market+code]
        k = stock.getKData(Query(-2))
        
        if len(k) < 2:
            return 0
            
        # 计算涨幅
        price_change = (k[-1].close - k[-2].close) / k[-2].close * 100
        
        # 根据涨幅调整成功率
        if price_change >= 9.5:  # 接近涨停
            success_rate = 0.3  # 30%成功率
        elif price_change >= 7:
            success_rate = 0.5  # 50%成功率
        elif price_change >= 5:
            success_rate = 0.7  # 70%成功率
        else:
            success_rate = 0.9  # 90%成功率
            
        # 随机决定成交量
        import random
        if random.random() > success_rate:
            return 0  # 未成交
            
        # 部分成交模拟
        actual_num = int(num * random.uniform(0.7, 1.0))
        return actual_num
```

### 撤单模拟

实际交易中，订单可能因为价格变动、等待时间过长等原因被撤销。

#### 订单有效期设置

```python
# 设置订单有效期
my_sys.setParam('max_delay', 3)  # 订单最多延迟3个周期

# 设置延迟买入/卖出
my_sys.setParam('buy_delay', True)   # 启用买入延迟
my_sys.setParam('sell_delay', True)  # 启用卖出延迟
```

#### 延迟成交机制

1. **信号生成**：在t时刻生成买入/卖出信号
2. **订单创建**：系统创建订单，但不立即执行
3. **延迟检查**：在后续t+1, t+2...时刻检查市场条件
4. **成交或撤单**：
   - 如果条件满足，订单成交
   - 如果超过最大延迟周期，订单自动撤销

#### 不同策略的延迟设置

| 策略类型 | 建议延迟设置 | 说明 |
|---------|------------|------|
| 日线策略 | 1-3天 | 考虑次日开盘价成交 |
| 分钟线策略 | 3-10分钟 | 短期价格波动大 |
| 高频策略 | 0-1分钟 | 追求立即成交 |
| 趋势策略 | 1-2天 | 容忍一定价格波动 |
| 反转策略 | 0-1天 | 时机敏感，不宜延迟 |

### 实际案例：首板策略交易模拟

以首板策略为例，综合考虑以上因素：

```python
# 创建适合首板策略的订单代理
first_board_broker = crtOB('OrderBrokerWrapper', {
    'buy_limit': 0.5,   # 首板买入成功率只有50%
    'sell_limit': 0.95, # 卖出成功率95%
})

# 创建A股交易成本模型
tc = crtTC('A_Stock', {
    'commission': 0.0003,
    'stamptax': 0.001,
    'min_commission': 5.0
})

# 创建滑点模型（首板通常滑点较大）
sp = crtSP('PercentSlippage', {'p': 0.005})  # 0.5%的滑点

# 设置到系统中
my_sys.sp = sp
my_tm = crtTM(init_cash=100000, tc=tc)
my_sys.tm = my_tm
my_sys.setParam('max_delay', 1)  # 最多延迟1天
my_sys.setParam('buy_delay', True)  # 启用买入延迟

# 运行回测
my_sys.run(stock, query, first_board_broker)
```

### 回测结果分析

通过这些模拟机制，可以分析不同因素对策略绩效的影响：

```python
# 基准回测（无滑点、无成本、100%成功率）
sys1 = System(tm1, mm)
sys1.sg = my_sg
sys1.run(stock, query)

# 考虑滑点
sys2 = System(tm2, mm)
sys2.sg = my_sg
sys2.sp = sp
sys2.run(stock, query)

# 考虑滑点和成本
sys3 = System(tm3, mm)
sys3.sg = my_sg
sys3.sp = sp
sys3.run(stock, query, None, tc)

# 考虑滑点、成本和成功率
sys4 = System(tm4, mm)
sys4.sg = my_sg
sys4.sp = sp
sys4.run(stock, query, broker, tc)

# 比较结果
print(f"基准年化收益率: {tm1.getAnnualReturn():.2%}")
print(f"考虑滑点后年化收益率: {tm2.getAnnualReturn():.2%}")
print(f"考虑滑点和成本后年化收益率: {tm3.getAnnualReturn():.2%}")
print(f"考虑所有因素后年化收益率: {tm4.getAnnualReturn():.2%}")
```

### 实盘与回测的差异

尽管Hikyuu提供了这些模拟机制，但实盘交易仍有一些无法完全模拟的因素：

| 因素 | 回测处理 | 实盘情况 | 差异影响 |
|------|---------|---------|---------|
| **市场冲击** | 简化模拟 | 大单会影响市场价格 | 实盘滑点可能更大 |
| **高频数据** | 基于K线 | 分笔成交和盘口变化 | 实盘可能有更多机会或风险 |
| **流动性突变** | 静态模拟 | 动态变化 | 极端情况下差异显著 |
| **交易系统延迟** | 忽略或固定值 | 不可预测 | 可能错过最佳时机 |
| **突发事件** | 难以模拟 | 经常发生 | 可能导致意外亏损 |

### 实盘策略调整建议

1. **保守估计**：
   - 回测时使用比预期更高的滑点
   - 使用更低的交易成功率
   - 考虑更高的交易成本

2. **分阶段部署**：
   - 先以较小资金测试
   - 逐步增加资金规模
   - 持续监控实际成交情况

3. **动态参数调整**：
   - 根据市场状况调整滑点估计
   - 在高波动期降低仓位或提高成功率要求
   - 定期校准模型参数与实际情况

通过这些机制和调整策略，可以使Hikyuu的回测结果更接近实际交易情况，开发出更加稳健的交易策略。
