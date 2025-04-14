"""
PyBacktest高级演示策略 - 多因子策略回测示例

本示例展示了如何使用PyBacktest框架实现一个多因子策略的回测。
策略逻辑：
1. 结合均线交叉、MACD和RSI三个因子生成综合信号
2. 当综合信号为正时买入，为负时卖出
3. 实现止损和止盈机制
4. 对多只股票进行回测，构建投资组合
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
    CrossSignal, MACDSignal, RSISignal, CompositeSignal,
    SignalStrategy, MultiSignalStrategy, PortfolioStrategy,
    Backtest
)

def download_stock_data(symbols, start_date, end_date, save_dir=None):
    """
    使用akshare下载多只股票的历史数据
    
    Args:
        symbols (list): 股票代码列表，例如['AAPL', 'MSFT']（美股）或['600000', '000001']（A股）
        start_date (str): 开始日期，格式'YYYY-MM-DD'
        end_date (str): 结束日期，格式'YYYY-MM-DD'
        save_dir (str, optional): 保存目录，如果提供则保存到CSV文件
        
    Returns:
        dict: 股票代码到DataFrame的映射
    """
    print(f"使用akshare下载 {len(symbols)} 只股票从 {start_date} 到 {end_date} 的历史数据...")
    
    data_dict = {}
    
    for symbol in symbols:
        print(f"下载 {symbol} 的数据...")
        
        # 检查是否已有保存的数据
        if save_dir:
            data_path = os.path.join(save_dir, f"{symbol}_data.csv")
            if os.path.exists(data_path):
                print(f"从 {data_path} 加载数据...")
                data = pd.read_csv(data_path, index_col=0, parse_dates=True)
                data_dict[symbol] = data
                continue
        
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
            
            # 如果提供了保存目录，则保存到CSV文件
            if save_dir:
                os.makedirs(save_dir, exist_ok=True)
                data_path = os.path.join(save_dir, f"{symbol}_data.csv")
                data.to_csv(data_path)
                print(f"数据已保存到 {data_path}")
            
            data_dict[symbol] = data
            
            # 添加延迟，避免频繁请求
            time.sleep(1)
            
        except Exception as e:
            print(f"下载 {symbol} 数据时出错: {e}")
            # 如果下载失败，创建示例数据
            print(f"为 {symbol} 创建示例数据...")
            data_dict[symbol] = create_sample_data(symbol, start_date, end_date)
    
    return data_dict

def create_sample_data(symbol, start_date='2020-01-01', end_date='2021-12-31'):
    """创建示例数据"""
    # 生成日期范围
    date_range = pd.date_range(start=start_date, end=end_date, freq='B')
    
    # 生成随机价格数据
    np.random.seed(hash(symbol) % 10000)  # 使用股票代码作为随机种子，使不同股票有不同的数据
    
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

class CustomStrategy(SignalStrategy):
    """自定义策略类，增加止损和止盈功能"""
    
    def __init__(self, signal_generator, symbol, stop_loss_pct=0.05, take_profit_pct=0.1, name="CustomStrategy"):
        """
        初始化自定义策略
        
        Args:
            signal_generator (SignalGenerator): 信号生成器
            symbol (str): 股票代码
            stop_loss_pct (float): 止损百分比，默认5%
            take_profit_pct (float): 止盈百分比，默认10%
            name (str): 策略名称
        """
        super().__init__(signal_generator, symbol, name)
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
    
    def run(self, data, trade_manager, initial_cash=None, position_size=None, position_pct=None):
        """
        运行策略
        
        Args:
            data (pd.DataFrame): 股票数据
            trade_manager (TradeManager): 交易管理器
            initial_cash (float, optional): 初始资金，如果提供则重置交易管理器
            position_size (int, optional): 每次交易的股数
            position_pct (float, optional): 每次交易的资金比例，0-1之间
            
        Returns:
            pd.DataFrame: 包含交易信号和结果的DataFrame
        """
        # 如果提供了初始资金，重置交易管理器
        if initial_cash is not None:
            trade_manager.reset()
        
        # 生成信号
        df = self.generate_signals(data)
        
        # 添加交易结果列
        df['trade_type'] = None
        df['shares'] = 0
        df['price'] = df['close']
        df['cash'] = trade_manager.cash
        df['position'] = 0
        df['portfolio_value'] = trade_manager.cash
        df['stop_loss'] = 0
        df['take_profit'] = 0
        
        # 记录买入价格，用于计算止损和止盈
        buy_price = 0
        
        # 遍历数据执行交易
        for i, row in df.iterrows():
            current_price = row['close']
            current_date = i
            
            # 更新持仓信息
            position = trade_manager.get_position(self.symbol)
            df.at[i, 'position'] = position.shares
            
            # 计算投资组合价值
            portfolio_value = trade_manager.cash
            if position.shares > 0:
                portfolio_value += position.market_value(current_price)
            df.at[i, 'portfolio_value'] = portfolio_value
            
            # 检查止损和止盈条件
            if position.shares > 0 and buy_price > 0:
                # 计算当前亏损百分比
                loss_pct = (buy_price - current_price) / buy_price
                # 计算当前盈利百分比
                profit_pct = (current_price - buy_price) / buy_price
                
                # 更新止损和止盈价格
                df.at[i, 'stop_loss'] = buy_price * (1 - self.stop_loss_pct)
                df.at[i, 'take_profit'] = buy_price * (1 + self.take_profit_pct)
                
                # 如果触发止损
                if loss_pct >= self.stop_loss_pct:
                    trade_record = trade_manager.sell(
                        date=current_date,
                        symbol=self.symbol,
                        price=current_price,
                        shares=position.shares
                    )
                    
                    if trade_record:
                        df.at[i, 'trade_type'] = 'SELL_STOP_LOSS'
                        df.at[i, 'shares'] = trade_record.shares
                        df.at[i, 'cash'] = trade_record.cash_balance
                        buy_price = 0
                    
                    continue
                
                # 如果触发止盈
                if profit_pct >= self.take_profit_pct:
                    trade_record = trade_manager.sell(
                        date=current_date,
                        symbol=self.symbol,
                        price=current_price,
                        shares=position.shares
                    )
                    
                    if trade_record:
                        df.at[i, 'trade_type'] = 'SELL_TAKE_PROFIT'
                        df.at[i, 'shares'] = trade_record.shares
                        df.at[i, 'cash'] = trade_record.cash_balance
                        buy_price = 0
                    
                    continue
            
            # 根据信号执行交易
            if row['signal'] == 1 and position.shares == 0:  # 买入信号且当前无持仓
                # 计算买入股数
                if position_size is not None:
                    shares = position_size
                elif position_pct is not None:
                    amount = trade_manager.cash * position_pct
                    shares = None
                else:
                    # 默认使用所有可用资金的90%
                    amount = trade_manager.cash * 0.9
                    shares = None
                
                # 执行买入
                trade_record = trade_manager.buy(
                    date=current_date,
                    symbol=self.symbol,
                    price=current_price,
                    shares=shares,
                    amount=amount if shares is None else None
                )
                
                if trade_record:
                    df.at[i, 'trade_type'] = 'BUY'
                    df.at[i, 'shares'] = trade_record.shares
                    df.at[i, 'cash'] = trade_record.cash_balance
                    buy_price = current_price  # 记录买入价格
            
            elif row['signal'] == -1 and position.shares > 0:  # 卖出信号且当前有持仓
                # 执行卖出
                trade_record = trade_manager.sell(
                    date=current_date,
                    symbol=self.symbol,
                    price=current_price,
                    shares=position.shares
                )
                
                if trade_record:
                    df.at[i, 'trade_type'] = 'SELL'
                    df.at[i, 'shares'] = trade_record.shares
                    df.at[i, 'cash'] = trade_record.cash_balance
                    buy_price = 0
            
            # 更新投资组合价值
            trade_manager.update_portfolio_value(
                date=current_date,
                price_dict={self.symbol: current_price}
            )
        
        return df

def create_multi_factor_strategy(symbol, stop_loss_pct=0.05, take_profit_pct=0.1):
    """
    创建多因子策略
    
    Args:
        symbol (str): 股票代码
        stop_loss_pct (float): 止损百分比
        take_profit_pct (float): 止盈百分比
        
    Returns:
        CustomStrategy: 自定义策略对象
    """
    # 创建各个信号生成器
    cross_signal = CrossSignal(fast_ma='ma5', slow_ma='ma20')
    macd_signal = MACDSignal()
    rsi_signal = RSISignal(overbought=70, oversold=30)
    
    # 创建组合信号生成器
    composite_signal = CompositeSignal(
        signal_generators=[cross_signal, macd_signal, rsi_signal],
        weights=[0.5, 0.3, 0.2]
    )
    
    # 创建自定义策略
    strategy = CustomStrategy(
        signal_generator=composite_signal,
        symbol=symbol,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        name=f"MultiFactorStrategy_{symbol}"
    )
    
    return strategy

def run_portfolio_backtest(data_dict, symbols, initial_cash=100000.0, commission_rate=0.0003, 
                          slippage_rate=0.0001, stop_loss_pct=0.05, take_profit_pct=0.1):
    """
    运行投资组合回测
    
    Args:
        data_dict (dict): 股票数据字典，键为股票代码，值为DataFrame
        symbols (list): 股票代码列表
        initial_cash (float): 初始资金
        commission_rate (float): 佣金率
        slippage_rate (float): 滑点率
        stop_loss_pct (float): 止损百分比
        take_profit_pct (float): 止盈百分比
        
    Returns:
        tuple: (回测结果字典, 回测引擎对象)
    """
    print(f"运行投资组合回测，包含 {len(symbols)} 只股票...")
    
    # 创建数据处理器
    data_handler = DataHandler()
    
    # 加载数据
    for symbol, data in data_dict.items():
        if symbol in symbols:
            data_handler.load_dataframe(symbol, data)
    
    # 创建交易成本对象
    trade_cost = TradeCost(
        commission_rate=commission_rate,
        min_commission=5.0,
        slippage_rate=slippage_rate
    )
    
    # 创建交易管理器
    trade_manager = TradeManager(initial_cash=initial_cash, trade_cost=trade_cost)
    
    # 创建策略字典
    strategies = {}
    for symbol in symbols:
        strategies[symbol] = create_multi_factor_strategy(
            symbol=symbol,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )
    
    # 创建投资组合策略
    portfolio_strategy = PortfolioStrategy(strategies)
    
    # 创建回测引擎
    backtest = Backtest(data_handler, trade_manager)
    
    # 运行投资组合回测
    results = backtest.run_portfolio(
        portfolio_strategy=portfolio_strategy,
        data_dict={symbol: data_dict[symbol] for symbol in symbols},
        position_pct={symbol: 1.0 / len(symbols) for symbol in symbols}  # 平均分配资金
    )
    
    return results, backtest

def analyze_portfolio_results(backtest, symbols, save_dir=None):
    """
    分析投资组合回测结果并生成图表
    
    Args:
        backtest (Backtest): 回测引擎对象
        symbols (list): 股票代码列表
        save_dir (str, optional): 保存图表的目录
    """
    print("分析投资组合回测结果...")
    
    # 打印绩效报告
    print("\n投资组合绩效报告:")
    backtest.performance.print_report()
    
    # 如果提供了保存目录，则创建目录
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
    
    # 绘制权益曲线
    plt.figure(figsize=(12, 6))
    equity_curve = backtest.plot_equity_curve()
    if save_dir:
        equity_curve.savefig(os.path.join(save_dir, "portfolio_equity_curve.png"))
    
    # 绘制回撤曲线
    plt.figure(figsize=(12, 6))
    drawdown_plot = backtest.plot_drawdown()
    if save_dir:
        drawdown_plot.savefig(os.path.join(save_dir, "portfolio_drawdown.png"))
    
    # 绘制月度收益热图
    plt.figure(figsize=(12, 8))
    monthly_returns_plot = backtest.plot_monthly_returns()
    if save_dir:
        monthly_returns_plot.savefig(os.path.join(save_dir, "portfolio_monthly_returns.png"))
    
    # 为每只股票绘制交易点位
    for symbol in symbols:
        plt.figure(figsize=(12, 6))
        trades_plot = backtest.plot_trades(symbol)
        if save_dir:
            trades_plot.savefig(os.path.join(save_dir, f"{symbol}_trades.png"))
    
    # 保存回测结果
    if save_dir:
        backtest.save_results(os.path.join(save_dir, "portfolio_backtest_results.xlsx"))
    
    print(f"\n分析完成，结果已保存到 {save_dir}")

def main():
    """主函数"""
    # 设置参数
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN"]  # 股票代码列表，美股使用股票代码如"AAPL"，A股使用数字代码如"600000"
    # 如果要测试A股，可以使用以下代码
    # symbols = ["600000", "000001", "600036", "601318"]
    start_date = "2018-01-01"  # 开始日期
    end_date = "2023-01-01"    # 结束日期
    initial_cash = 1000000.0   # 初始资金
    
    # 创建结果保存目录
    results_dir = "portfolio_backtest_results"
    os.makedirs(results_dir, exist_ok=True)
    
    # 下载或加载股票数据
    data_dict = download_stock_data(symbols, start_date, end_date, results_dir)
    
    # 运行投资组合回测
    results, backtest = run_portfolio_backtest(
        data_dict=data_dict,
        symbols=symbols,
        initial_cash=initial_cash,
        commission_rate=0.0003,
        slippage_rate=0.0001,
        stop_loss_pct=0.05,
        take_profit_pct=0.1
    )
    
    # 分析回测结果
    analyze_portfolio_results(backtest, symbols, results_dir)
    
    # 显示图表
    plt.show()

if __name__ == "__main__":
    main()
