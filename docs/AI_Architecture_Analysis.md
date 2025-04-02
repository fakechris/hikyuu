# Hikyuu Quant Framework 架构分析

本文档是对 Hikyuu Quant Framework 项目的架构分析，包括整体架构模式、模块划分与依赖关系、核心技术栈及主要业务流程。

## 1. 整体架构模式

Hikyuu 采用**分层架构**与**组件化设计模式**，主要分为三层：

1. **C++ 核心库**：提供高性能的计算引擎和策略框架
2. **Python 包装层**：提供对 C++ 库的包装，便于使用
3. **交互式工具层**：基于 Python 的交互式探索和回测工具

这种架构设计实现了性能与易用性的平衡，通过 C++ 保证性能，通过 Python 提供灵活性和易用性。

## 2. 核心技术栈

### 编程语言与框架
- **C++17**：核心库实现语言
- **Python**：包装层和交互式工具
- **Boost**：C++ 库依赖
- **PyBind11**：C++/Python 绑定

### 构建工具
- **XMake**：跨平台构建系统，支持多种编译模式（debug, release）

### 数据存储
- **HDF5**：默认数据存储格式，文件体积小、速度快、备份便捷
- **MySQL**：可选数据存储方式
- **SQLite**：轻量级数据存储
- **SQLAlchemy**：Python ORM 工具

### 第三方库
#### C++ 依赖：
- **boost (1.87.0)**：C++ 基础库
- **hdf5 (1.12.2)**：数据存储
- **fmt (11.1.4)**：格式化库
- **spdlog (1.15.1)**：日志库
- **flatbuffers (24.3.25)**：序列化
- **nng (1.10.1)**：网络通信
- **sqlite (3.49.0)**：轻量级数据库
- **nlohmann_json**：JSON 处理
- **ta-lib**：技术分析库

#### Python 依赖：
- **numpy**：数值计算
- **matplotlib/seaborn**：绘图
- **pandas**：数据分析
- **PyQt5**：GUI 界面
- **tables**：HDF5 接口
- **bokeh/pyecharts**：交互式图表
- **pytdx**：通达信数据接口
- **akshare**：金融数据接口

## 3. 模块划分与依赖关系

### 核心模块

1. **数据管理模块**
   - `StockManager`：核心单例类，管理所有股票数据和市场信息
   - `Stock`：股票类，包含股票基本信息
   - `KData`：K线数据类
   - `MarketInfo`：市场信息类
   - `Block`：板块类

2. **数据驱动模块**
   - `data_driver`：数据驱动接口
   - 支持 HDF5、MySQL、SQLite 和通达信格式

3. **指标系统**
   - `indicator`：技术指标系统
   - `Indicator`：指标基类
   - `IndicatorImp`：指标实现类
   - 集成 ta-lib 库的技术指标

4. **交易管理模块**
   - `trade_manage`：交易管理
   - `TradeManager`：交易管理器
   - `TradeCost`：交易成本计算
   - `Performance`：绩效评估

5. **交易系统模块**
   - `trade_sys`：交易系统组件
   - 包含多个子模块：
     - `environment`：市场环境判断
     - `condition`：系统有效条件
     - `signal`：信号指示器
     - `stoploss`：止损策略
     - `moneymanager`：资金管理
     - `profitgoal`：盈利目标
     - `slippage`：滑点模型
     - `selector`：选股策略
     - `allocatefunds`：资金分配
     - `portfolio`：投资组合
     - `system`：交易系统

6. **策略模块**
   - `strategy`：策略定义和实现
   - `Strategy`：策略基类

7. **分析模块**
   - `analysis`：策略分析工具
   - 回测结果分析和评估

8. **工具模块**
   - `utilities`：工具函数
   - 包含日期时间处理、参数管理等

### 依赖关系

- **核心依赖链**：数据驱动模块 → 数据管理模块 → 指标系统 → 交易管理模块 → 交易系统模块 → 策略模块 → 分析模块
- **工具模块**：被所有其他模块依赖

## 4. 主入口点和关键配置文件

### 主入口点
- C++ 核心库入口：`hikyuu_cpp/hikyuu/hikyuu.h` 和 `hikyuu.cpp`
- Python 包入口：`hikyuu/__init__.py`
- 主要初始化函数：`hikyuu_init()` 和 `load_hikyuu()`

### 关键配置文件
- 构建配置：`xmake.lua`
- Python 包配置：`setup.py`
- 依赖配置：`requirements.txt`
- 项目配置模板：`hikyuu/config` 目录下的配置文件

## 5. 核心领域模型与业务流程

### 核心领域模型
1. **Stock**：股票模型，包含基本信息和K线数据
2. **KData**：K线数据模型
3. **TradeManager**：交易管理模型
4. **System**：交易系统模型
5. **Portfolio**：投资组合模型

### 实体类关系
- Stock 1:n KData：一个股票包含多种周期的K线数据
- StockManager 1:n Stock：管理多个股票
- TradeManager 1:n TradeRecord：管理多个交易记录
- System 组合了多个交易组件：Signal、MoneyManager、StopLoss 等
- Portfolio 管理多个 System

### 主要业务流程
1. **数据加载流程**：
   - 初始化 StockManager
   - 加载市场信息、股票信息、K线数据
   - 预处理数据

2. **策略回测流程**：
   - 创建交易管理器
   - 配置交易系统组件
   - 运行回测
   - 分析结果

3. **实时交易流程**：
   - 数据实时更新
   - 信号生成
   - 交易执行

## 6. 设计模式应用

1. **单例模式**：StockManager 采用单例模式
2. **工厂模式**：用于创建各种组件实例
3. **策略模式**：交易系统的各个组件采用策略模式
4. **组合模式**：交易系统组件的组合
5. **观察者模式**：信号系统的实现

## 总结

Hikyuu Quant Framework 是一个模块化、可扩展的量化交易研究框架，采用 C++/Python 混合架构，兼顾了性能和易用性。其核心思想是将系统化交易抽象为多个组件，允许用户灵活组合这些组件来构建和测试交易策略。框架支持多种数据存储方式，并提供了丰富的技术指标和交易系统组件，适合进行量化策略研究和回测。
