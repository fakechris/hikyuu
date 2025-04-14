"""
PyBacktest示例脚本
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
from pybacktest import (
    DataHandler, TradeManager, TradeCost, 
    CrossSignal, MACDSignal, RSISignal,
    SignalStrategy, MultiSignalStrategy, PortfolioStrategy,
    Backtest
)

# 创建示例数据
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

# 主函数
def main():
    # 创建数据处理器
    data_handler = DataHandler()
    
    # 加载示例数据
    symbol = 'SAMPLE'
    data = create_sample_data(symbol)
    data_handler.load_dataframe(symbol, data)
    
    # 创建交易成本对象
    trade_cost = TradeCost(commission_rate=0.0003, min_commission=5.0, slippage_rate=0.0001)
    
    # 创建交易管理器
    trade_manager = TradeManager(initial_cash=100000.0, trade_cost=trade_cost)
    
    # 创建信号生成器
    cross_signal = CrossSignal(fast_ma='ma5', slow_ma='ma20')
    macd_signal = MACDSignal()
    rsi_signal = RSISignal()
    
    # 创建策略
    strategy1 = SignalStrategy(cross_signal, symbol)
    strategy2 = SignalStrategy(macd_signal, symbol)
    strategy3 = SignalStrategy(rsi_signal, symbol)
    
    # 创建多信号策略
    multi_strategy = MultiSignalStrategy(
        signal_generators=[cross_signal, macd_signal, rsi_signal],
        symbol=symbol,
        weights=[0.5, 0.3, 0.2]
    )
    
    # 创建回测引擎
    backtest = Backtest(data_handler, trade_manager)
    
    # 运行回测
    print("运行均线交叉策略回测...")
    result1 = backtest.run(strategy1, symbol, position_pct=0.9)
    
    # 打印绩效报告
    print("\n均线交叉策略绩效报告:")
    backtest.performance.print_report()
    
    # 绘制权益曲线
    plt.figure(figsize=(12, 6))
    plt.plot(result1.index, result1['portfolio_value'])
    plt.title('均线交叉策略权益曲线')
    plt.xlabel('日期')
    plt.ylabel('价值')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('equity_curve.png')
    
    # 绘制交易点位
    backtest.plot_trades(symbol)
    plt.savefig('trades.png')
    
    # 重置交易管理器
    trade_manager.reset()
    
    # 运行多信号策略回测
    print("\n运行多信号策略回测...")
    result2 = backtest.run(multi_strategy, symbol, initial_cash=100000.0, position_pct=0.9)
    
    # 打印绩效报告
    print("\n多信号策略绩效报告:")
    backtest.performance.print_report()
    
    # 绘制权益曲线
    plt.figure(figsize=(12, 6))
    plt.plot(result2.index, result2['portfolio_value'])
    plt.title('多信号策略权益曲线')
    plt.xlabel('日期')
    plt.ylabel('价值')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig('multi_signal_equity_curve.png')
    
    # 绘制回撤曲线
    backtest.plot_drawdown()
    plt.savefig('drawdown.png')
    
    # 保存回测结果
    backtest.save_results('backtest_results.xlsx')
    
    print("\n回测完成，结果已保存到backtest_results.xlsx")
    print("图表已保存到equity_curve.png, trades.png, multi_signal_equity_curve.png和drawdown.png")

if __name__ == "__main__":
    main()
