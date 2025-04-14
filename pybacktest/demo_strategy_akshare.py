"""
PyBacktest演示策略 - 双均线交叉策略回测示例

本示例展示了如何使用PyBacktest框架实现一个双均线交叉策略的回测。
策略逻辑：
1. 当短期均线(MA5)上穿长期均线(MA20)时买入
2. 当短期均线(MA5)下穿长期均线(MA20)时卖出
3. 每次使用账户90%的资金进行交易
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import os
import akshare as ak  # 用于下载股票数据
import time

# 导入PyBacktest模块
from pybacktest import (
    DataHandler, TradeManager, TradeCost, 
    CrossSignal, SignalStrategy, Backtest
)

def download_stock_data(symbol, start_date, end_date, save_path=None):
    """
    使用akshare下载股票历史数据
    
    Args:
        symbol (str): 股票代码，例如'AAPL'（美股）或'600000'（A股）
        start_date (str): 开始日期，格式'YYYY-MM-DD'
        end_date (str): 结束日期，格式'YYYY-MM-DD'
        save_path (str, optional): 保存路径，如果提供则保存到CSV文件
        
    Returns:
        pd.DataFrame: 股票历史数据
    """
    print(f"使用akshare下载 {symbol} 从 {start_date} 到 {end_date} 的历史数据...")
    
    try:
        # 判断是美股还是A股
        if symbol.isalpha():  # 纯字母为美股代码
            # 下载美股数据
            data = ak.stock_us_daily(symbol=symbol, adjust="qfq")
            # 筛选日期范围
            data = data[(data['date'] >= start_date) & (data['date'] <= end_date)]
            # 重命名列
            data = data.rename(columns={
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
        else:  # 否则假设为A股代码
            # 下载A股数据
            if symbol.startswith('6'):
                symbol_with_prefix = f"sh{symbol}"
            else:
                symbol_with_prefix = f"sz{symbol}"
            
            data = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date, end_date=end_date, adjust="qfq")
            # 重命名列
            data = data.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '最高': 'high',
                '最低': 'low',
                '收盘': 'close',
                '成交量': 'volume'
            })
        
        # 设置日期为索引
        data['date'] = pd.to_datetime(data['date'])
        data.set_index('date', inplace=True)
        
        # 确保所有价格列是数值类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            data[col] = pd.to_numeric(data[col], errors='coerce')
        
        # 如果提供了保存路径，则保存到CSV文件
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            data.to_csv(save_path)
            print(f"数据已保存到 {save_path}")
        
        return data
    
    except Exception as e:
        print(f"下载数据时出错: {e}")
        # 如果下载失败，尝试创建一个示例数据集
        print("创建示例数据集...")
        return create_sample_data(symbol, start_date, end_date)

def create_sample_data(symbol, start_date='2020-01-01', end_date='2021-12-31'):
    """创建示例数据"""
    # 生成日期范围
    date_range = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 生成随机价格数据
    np.random.seed(42)  # 设置随机种子，使结果可重现
    
    # 初始价格
    initial_price = 100.0
    
    # 生成价格数据
    prices = [initial_price]
    for _ in range(1, len(date_range)):
        # 生成-1%到1%之间的随机价格变动
        change = np.random.normal(0.0005, 0.01)
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # 创建DataFrame
    df = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + np.random.uniform(0, 0.01)) for p in prices],
        'low': [p * (1 - np.random.uniform(0, 0.01)) for p in prices],
        'close': prices,
        'volume': np.random.randint(1000, 100000, size=len(date_range))
    }, index=date_range)
    
    return df

def run_ma_cross_strategy(symbol, data, initial_cash=100000.0, commission_rate=0.0003, 
                         slippage_rate=0.0001, fast_ma='ma5', slow_ma='ma20'):
    """
    运行双均线交叉策略回测
    
    Args:
        symbol (str): 股票代码
        data (pd.DataFrame): 股票历史数据
        initial_cash (float): 初始资金
        commission_rate (float): 佣金率
        slippage_rate (float): 滑点率
        fast_ma (str): 快速均线列名
        slow_ma (str): 慢速均线列名
        
    Returns:
        tuple: (回测结果DataFrame, 回测引擎对象)
    """
    print(f"运行 {symbol} 的双均线交叉策略回测...")
    
    # 创建数据处理器
    data_handler = DataHandler()
    
    # 加载数据
    data_handler.load_dataframe(symbol, data)
    
    # 创建交易成本对象
    trade_cost = TradeCost(
        commission_rate=commission_rate,
        min_commission=5.0,
        slippage_rate=slippage_rate
    )
    
    # 创建交易管理器
    trade_manager = TradeManager(initial_cash=initial_cash, trade_cost=trade_cost)
    
    # 创建信号生成器 - 均线交叉
    cross_signal = CrossSignal(fast_ma=fast_ma, slow_ma=slow_ma)
    
    # 创建策略
    strategy = SignalStrategy(cross_signal, symbol)
    
    # 创建回测引擎
    backtest = Backtest(data_handler, trade_manager)
    
    # 运行回测
    result = backtest.run(strategy, symbol, position_pct=0.9)
    
    return result, backtest

def analyze_results(backtest, symbol, save_dir=None):
    """
    分析回测结果并生成图表
    
    Args:
        backtest (Backtest): 回测引擎对象
        symbol (str): 股票代码
        save_dir (str, optional): 保存图表的目录
    """
    print("分析回测结果...")
    
    # 打印绩效报告
    print("\n绩效报告:")
    backtest.performance.print_report()
    
    # 如果提供了保存目录，则创建目录
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    
    # 绘制权益曲线
    plt.figure(figsize=(12, 6))
    equity_curve = backtest.plot_equity_curve()
    if save_dir:
        equity_curve.savefig(os.path.join(save_dir, f"{symbol}_equity_curve.png"))
    
    # 绘制交易点位
    plt.figure(figsize=(12, 6))
    trades_plot = backtest.plot_trades(symbol)
    if save_dir:
        trades_plot.savefig(os.path.join(save_dir, f"{symbol}_trades.png"))
    
    # 绘制回撤曲线
    plt.figure(figsize=(12, 6))
    drawdown_plot = backtest.plot_drawdown()
    if save_dir:
        drawdown_plot.savefig(os.path.join(save_dir, f"{symbol}_drawdown.png"))
    
    # 绘制月度收益热图
    plt.figure(figsize=(12, 8))
    monthly_returns_plot = backtest.plot_monthly_returns()
    if save_dir:
        monthly_returns_plot.savefig(os.path.join(save_dir, f"{symbol}_monthly_returns.png"))
    
    # 保存回测结果
    if save_dir:
        backtest.save_results(os.path.join(save_dir, f"{symbol}_backtest_results.xlsx"))
    
    print(f"\n分析完成，结果已保存到 {save_dir}")

def main():
    """主函数"""
    # 设置参数
    symbol = "AAPL"  # 股票代码，美股使用股票代码如"AAPL"，A股使用数字代码如"600000"
    start_date = "2018-01-01"  # 开始日期
    end_date = "2023-01-01"    # 结束日期
    initial_cash = 100000.0    # 初始资金
    
    # 创建结果保存目录
    results_dir = "backtest_results"
    os.makedirs(results_dir, exist_ok=True)
    
    # 下载或加载股票数据
    data_path = os.path.join(results_dir, f"{symbol}_data.csv")
    
    if os.path.exists(data_path):
        print(f"从 {data_path} 加载数据...")
        data = pd.read_csv(data_path, index_col=0, parse_dates=True)
    else:
        data = download_stock_data(symbol, start_date, end_date, data_path)
    
    # 运行双均线交叉策略回测
    result, backtest = run_ma_cross_strategy(
        symbol=symbol,
        data=data,
        initial_cash=initial_cash,
        commission_rate=0.0003,
        slippage_rate=0.0001,
        fast_ma='ma5',
        slow_ma='ma20'
    )
    
    # 分析回测结果
    analyze_results(backtest, symbol, results_dir)
    
    # 显示图表
    plt.show()

if __name__ == "__main__":
    main()
