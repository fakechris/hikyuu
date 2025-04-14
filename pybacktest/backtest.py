"""
回测引擎模块 - 负责执行回测
"""
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from .data import DataHandler
from .trade import TradeManager, TradeCost
from .signal import SignalGenerator
from .strategy import Strategy
from .performance import Performance


class Backtest:
    """回测引擎类"""
    
    def __init__(self, data_handler=None, trade_manager=None):
        """初始化回测引擎
        
        Args:
            data_handler (DataHandler, optional): 数据处理器
            trade_manager (TradeManager, optional): 交易管理器
        """
        self.data_handler = data_handler if data_handler else DataHandler()
        self.trade_manager = trade_manager if trade_manager else TradeManager()
        self.results = {}
        self.performance = Performance()
    
    def run(self, strategy, symbol, start_date=None, end_date=None, initial_cash=None, position_size=None, position_pct=None):
        """运行回测
        
        Args:
            strategy (Strategy): 策略对象
            symbol (str): 股票代码
            start_date (str or datetime, optional): 开始日期
            end_date (str or datetime, optional): 结束日期
            initial_cash (float, optional): 初始资金
            position_size (int, optional): 每次交易的股数
            position_pct (float, optional): 每次交易的资金比例，0-1之间
            
        Returns:
            pd.DataFrame: 回测结果
        """
        # 获取数据
        data = self.data_handler.get_data(symbol, start_date, end_date)
        
        # 如果提供了初始资金，重置交易管理器
        if initial_cash is not None:
            self.trade_manager.initial_cash = initial_cash
            self.trade_manager.reset()
        
        # 运行策略
        result = strategy.run(
            data=data,
            trade_manager=self.trade_manager,
            position_size=position_size,
            position_pct=position_pct
        )
        
        # 保存结果
        self.results[symbol] = result
        
        # 计算绩效
        self.performance.calculate(self.trade_manager, result)
        
        return result
    
    def run_portfolio(self, portfolio_strategy, data_dict, start_date=None, end_date=None, initial_cash=None, position_pct=None):
        """运行投资组合回测
        
        Args:
            portfolio_strategy (PortfolioStrategy): 投资组合策略对象
            data_dict (dict): 数据字典，键为股票代码，值为DataFrame
            start_date (str or datetime, optional): 开始日期
            end_date (str or datetime, optional): 结束日期
            initial_cash (float, optional): 初始资金
            position_pct (float or dict, optional): 每只股票的资金比例，可以是单一值或字典
            
        Returns:
            dict: 包含每只股票交易结果的字典
        """
        # 处理日期范围
        filtered_data_dict = {}
        for symbol, data in data_dict.items():
            filtered_data = data.copy()
            
            if start_date is not None:
                if isinstance(start_date, str):
                    start_date = pd.to_datetime(start_date)
                filtered_data = filtered_data[filtered_data.index >= start_date]
            
            if end_date is not None:
                if isinstance(end_date, str):
                    end_date = pd.to_datetime(end_date)
                filtered_data = filtered_data[filtered_data.index <= end_date]
            
            filtered_data_dict[symbol] = filtered_data
        
        # 如果提供了初始资金，重置交易管理器
        if initial_cash is not None:
            self.trade_manager.initial_cash = initial_cash
            self.trade_manager.reset()
        
        # 运行投资组合策略
        results = portfolio_strategy.run(
            data_dict=filtered_data_dict,
            trade_manager=self.trade_manager,
            position_pct=position_pct
        )
        
        # 保存结果
        self.results = results
        
        # 计算投资组合绩效
        self.performance.calculate_portfolio(self.trade_manager, results)
        
        return results
    
    def get_performance(self):
        """获取绩效统计
        
        Returns:
            dict: 绩效统计字典
        """
        return self.performance.get_stats()
    
    def plot_equity_curve(self, benchmark=None):
        """绘制权益曲线
        
        Args:
            benchmark (pd.DataFrame, optional): 基准数据
        """
        portfolio_value_df = self.trade_manager.get_portfolio_value_df()
        
        if portfolio_value_df.empty:
            print("没有投资组合数据可供绘制")
            return
        
        plt.figure(figsize=(12, 6))
        
        # 绘制权益曲线
        plt.plot(portfolio_value_df.index, portfolio_value_df['total_value'], label='策略')
        
        # 如果有基准数据，绘制基准曲线
        if benchmark is not None:
            # 确保基准数据的索引是日期类型
            if not isinstance(benchmark.index, pd.DatetimeIndex):
                benchmark = benchmark.set_index('date')
            
            # 调整基准数据的起始值与策略相同
            benchmark_values = benchmark['close'] / benchmark['close'].iloc[0] * portfolio_value_df['total_value'].iloc[0]
            plt.plot(benchmark.index, benchmark_values, label='基准', alpha=0.7)
        
        plt.title('投资组合权益曲线')
        plt.xlabel('日期')
        plt.ylabel('价值')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        
        return plt.gcf()
    
    def plot_drawdown(self):
        """绘制回撤曲线"""
        portfolio_value_df = self.trade_manager.get_portfolio_value_df()
        
        if portfolio_value_df.empty:
            print("没有投资组合数据可供绘制")
            return
        
        # 计算回撤
        portfolio_value_df['peak'] = portfolio_value_df['total_value'].cummax()
        portfolio_value_df['drawdown'] = (portfolio_value_df['total_value'] - portfolio_value_df['peak']) / portfolio_value_df['peak'] * 100
        
        plt.figure(figsize=(12, 6))
        plt.plot(portfolio_value_df.index, portfolio_value_df['drawdown'])
        plt.fill_between(portfolio_value_df.index, portfolio_value_df['drawdown'], 0, alpha=0.3, color='red')
        plt.title('投资组合回撤曲线')
        plt.xlabel('日期')
        plt.ylabel('回撤 (%)')
        plt.grid(True)
        plt.tight_layout()
        
        return plt.gcf()
    
    def plot_monthly_returns(self):
        """绘制月度收益热图"""
        portfolio_value_df = self.trade_manager.get_portfolio_value_df()
        
        if portfolio_value_df.empty:
            print("没有投资组合数据可供绘制")
            return
        
        # 计算每日收益率
        portfolio_value_df['daily_return'] = portfolio_value_df['total_value'].pct_change()
        
        # 计算月度收益率
        monthly_returns = portfolio_value_df['daily_return'].resample('M').apply(lambda x: (1 + x).prod() - 1)
        monthly_returns = monthly_returns.to_frame()
        
        # 添加年份和月份列
        monthly_returns['year'] = monthly_returns.index.year
        monthly_returns['month'] = monthly_returns.index.month
        
        # 创建透视表
        pivot_table = monthly_returns.pivot_table(index='year', columns='month', values='daily_return')
        
        # 绘制热图
        plt.figure(figsize=(12, 8))
        sns.heatmap(pivot_table * 100, annot=True, fmt='.2f', cmap='RdYlGn', center=0, linewidths=1)
        plt.title('月度收益率热图 (%)')
        plt.xlabel('月份')
        plt.ylabel('年份')
        
        # 设置x轴标签为月份名称
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        plt.xticks(np.arange(12) + 0.5, month_names)
        
        plt.tight_layout()
        
        return plt.gcf()
    
    def plot_trades(self, symbol):
        """绘制交易点位
        
        Args:
            symbol (str): 股票代码
        """
        if symbol not in self.results:
            print(f"没有股票 {symbol} 的回测结果")
            return
        
        result = self.results[symbol]
        
        plt.figure(figsize=(12, 6))
        
        # 绘制价格曲线
        plt.plot(result.index, result['close'], label='价格')
        
        # 绘制买入点
        buy_points = result[result['trade_type'] == 'BUY']
        plt.scatter(buy_points.index, buy_points['price'], marker='^', color='green', s=100, label='买入')
        
        # 绘制卖出点
        sell_points = result[result['trade_type'] == 'SELL']
        plt.scatter(sell_points.index, sell_points['price'], marker='v', color='red', s=100, label='卖出')
        
        plt.title(f'{symbol} 交易点位')
        plt.xlabel('日期')
        plt.ylabel('价格')
        plt.grid(True)
        plt.legend()
        plt.tight_layout()
        
        return plt.gcf()
    
    def save_results(self, filepath):
        """保存回测结果
        
        Args:
            filepath (str): 文件路径
        """
        # 保存交易记录
        trade_history = pd.DataFrame([
            {
                'date': record.date,
                'symbol': record.symbol,
                'trade_type': record.trade_type.name,
                'price': record.price,
                'shares': record.shares,
                'commission': record.commission,
                'slippage': record.slippage,
                'total_cost': record.total_cost,
                'cash_change': record.cash_change,
                'cash_balance': record.cash_balance
            }
            for record in self.trade_manager.get_trade_history()
        ])
        
        # 保存绩效统计
        performance_stats = pd.DataFrame([self.performance.get_stats()])
        
        # 保存到Excel文件
        with pd.ExcelWriter(filepath) as writer:
            trade_history.to_excel(writer, sheet_name='交易记录', index=False)
            performance_stats.to_excel(writer, sheet_name='绩效统计', index=False)
            
            # 保存每只股票的回测结果
            for symbol, result in self.results.items():
                result.to_excel(writer, sheet_name=f'{symbol}回测结果')
            
            # 保存投资组合价值
            portfolio_value_df = self.trade_manager.get_portfolio_value_df()
            if not portfolio_value_df.empty:
                portfolio_value_df.to_excel(writer, sheet_name='投资组合价值')
