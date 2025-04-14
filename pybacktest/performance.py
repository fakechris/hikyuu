"""
绩效分析模块 - 负责计算和分析回测结果
"""
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
from .trade import TradeType


class Performance:
    """绩效分析类"""
    
    def __init__(self):
        """初始化绩效分析器"""
        self.stats = {}
        self.trade_stats = {}
        self.portfolio_stats = {}
    
    def calculate(self, trade_manager, result_df):
        """计算绩效统计
        
        Args:
            trade_manager (TradeManager): 交易管理器
            result_df (pd.DataFrame): 回测结果DataFrame
        """
        # 获取交易记录
        trade_history = trade_manager.get_trade_history()
        
        # 如果没有交易记录，返回空统计
        if len(trade_history) <= 1:  # 只有初始化记录
            self.stats = {
                'initial_cash': trade_manager.initial_cash,
                'final_cash': trade_manager.cash,
                'total_return': 0,
                'annual_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'max_profit': 0,
                'max_loss': 0,
                'avg_holding_days': 0
            }
            return
        
        # 计算基本统计
        initial_cash = trade_manager.initial_cash
        final_portfolio_value = result_df['portfolio_value'].iloc[-1]
        
        # 总收益率
        total_return = (final_portfolio_value / initial_cash - 1) * 100
        
        # 年化收益率
        start_date = result_df.index[0]
        end_date = result_df.index[-1]
        years = (end_date - start_date).days / 365
        annual_return = ((final_portfolio_value / initial_cash) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # 计算每日收益率
        result_df['daily_return'] = result_df['portfolio_value'].pct_change()
        
        # 计算最大回撤
        result_df['peak'] = result_df['portfolio_value'].cummax()
        result_df['drawdown'] = (result_df['portfolio_value'] - result_df['peak']) / result_df['peak'] * 100
        max_drawdown = result_df['drawdown'].min()
        
        # 计算夏普比率（假设无风险利率为0）
        daily_returns = result_df['daily_return'].dropna()
        sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if len(daily_returns) > 0 and daily_returns.std() > 0 else 0
        
        # 分析交易记录
        buy_trades = [t for t in trade_history if t.trade_type == TradeType.BUY]
        sell_trades = [t for t in trade_history if t.trade_type == TradeType.SELL]
        
        # 配对买卖交易
        paired_trades = []
        buy_index = 0
        sell_index = 0
        
        while buy_index < len(buy_trades) and sell_index < len(sell_trades):
            buy_trade = buy_trades[buy_index]
            sell_trade = sell_trades[sell_index]
            
            if sell_trade.date > buy_trade.date:
                # 找到一对交易
                paired_trades.append((buy_trade, sell_trade))
                buy_index += 1
                sell_index += 1
            else:
                # 卖出交易在买入交易之前，跳过
                sell_index += 1
        
        # 计算交易统计
        total_trades = len(paired_trades)
        winning_trades = 0
        losing_trades = 0
        break_even_trades = 0
        total_profit = 0
        total_loss = 0
        max_profit = 0
        max_loss = 0
        total_holding_days = 0
        
        for buy, sell in paired_trades:
            # 计算交易盈亏
            buy_value = buy.price * buy.shares + buy.total_cost
            sell_value = sell.price * sell.shares - sell.total_cost
            profit = sell_value - buy_value
            
            # 更新统计
            if profit > 0:
                winning_trades += 1
                total_profit += profit
                max_profit = max(max_profit, profit)
            elif profit < 0:
                losing_trades += 1
                total_loss += abs(profit)
                max_loss = max(max_loss, abs(profit))
            else:
                break_even_trades += 1
            
            # 计算持仓天数
            holding_days = (sell.date - buy.date).days
            total_holding_days += holding_days
        
        # 计算胜率和盈亏比
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0
        
        # 计算平均盈利和亏损
        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        # 计算平均持仓天数
        avg_holding_days = total_holding_days / total_trades if total_trades > 0 else 0
        
        # 保存统计结果
        self.stats = {
            'initial_cash': initial_cash,
            'final_portfolio_value': final_portfolio_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'break_even_trades': break_even_trades,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'avg_holding_days': avg_holding_days
        }
        
        # 保存交易统计
        self.trade_stats = {
            'paired_trades': paired_trades,
            'buy_trades': buy_trades,
            'sell_trades': sell_trades
        }
    
    def calculate_portfolio(self, trade_manager, results_dict):
        """计算投资组合绩效统计
        
        Args:
            trade_manager (TradeManager): 交易管理器
            results_dict (dict): 回测结果字典，键为股票代码，值为DataFrame
        """
        # 获取投资组合价值数据
        portfolio_value_df = trade_manager.get_portfolio_value_df()
        
        # 如果没有投资组合数据，返回空统计
        if portfolio_value_df.empty:
            self.stats = {
                'initial_cash': trade_manager.initial_cash,
                'final_cash': trade_manager.cash,
                'total_return': 0,
                'annual_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'win_rate': 0,
                'profit_factor': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'avg_profit': 0,
                'avg_loss': 0,
                'max_profit': 0,
                'max_loss': 0,
                'avg_holding_days': 0
            }
            return
        
        # 计算基本统计
        initial_cash = trade_manager.initial_cash
        final_portfolio_value = portfolio_value_df['total_value'].iloc[-1]
        
        # 总收益率
        total_return = (final_portfolio_value / initial_cash - 1) * 100
        
        # 年化收益率
        start_date = portfolio_value_df.index[0]
        end_date = portfolio_value_df.index[-1]
        years = (end_date - start_date).days / 365
        annual_return = ((final_portfolio_value / initial_cash) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # 计算每日收益率
        portfolio_value_df['daily_return'] = portfolio_value_df['total_value'].pct_change()
        
        # 计算最大回撤
        portfolio_value_df['peak'] = portfolio_value_df['total_value'].cummax()
        portfolio_value_df['drawdown'] = (portfolio_value_df['total_value'] - portfolio_value_df['peak']) / portfolio_value_df['peak'] * 100
        max_drawdown = portfolio_value_df['drawdown'].min()
        
        # 计算夏普比率（假设无风险利率为0）
        daily_returns = portfolio_value_df['daily_return'].dropna()
        sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if len(daily_returns) > 0 and daily_returns.std() > 0 else 0
        
        # 获取交易记录
        trade_history = trade_manager.get_trade_history()
        
        # 分析交易记录
        buy_trades = [t for t in trade_history if t.trade_type == TradeType.BUY]
        sell_trades = [t for t in trade_history if t.trade_type == TradeType.SELL]
        
        # 按股票分组
        trades_by_symbol = {}
        for trade in trade_history:
            if trade.symbol:
                if trade.symbol not in trades_by_symbol:
                    trades_by_symbol[trade.symbol] = []
                trades_by_symbol[trade.symbol].append(trade)
        
        # 配对买卖交易
        paired_trades = []
        for symbol, trades in trades_by_symbol.items():
            buy_trades = [t for t in trades if t.trade_type == TradeType.BUY]
            sell_trades = [t for t in trades if t.trade_type == TradeType.SELL]
            
            buy_index = 0
            sell_index = 0
            
            while buy_index < len(buy_trades) and sell_index < len(sell_trades):
                buy_trade = buy_trades[buy_index]
                sell_trade = sell_trades[sell_index]
                
                if sell_trade.date > buy_trade.date:
                    # 找到一对交易
                    paired_trades.append((buy_trade, sell_trade))
                    buy_index += 1
                    sell_index += 1
                else:
                    # 卖出交易在买入交易之前，跳过
                    sell_index += 1
        
        # 计算交易统计
        total_trades = len(paired_trades)
        winning_trades = 0
        losing_trades = 0
        break_even_trades = 0
        total_profit = 0
        total_loss = 0
        max_profit = 0
        max_loss = 0
        total_holding_days = 0
        
        for buy, sell in paired_trades:
            # 计算交易盈亏
            buy_value = buy.price * buy.shares + buy.total_cost
            sell_value = sell.price * sell.shares - sell.total_cost
            profit = sell_value - buy_value
            
            # 更新统计
            if profit > 0:
                winning_trades += 1
                total_profit += profit
                max_profit = max(max_profit, profit)
            elif profit < 0:
                losing_trades += 1
                total_loss += abs(profit)
                max_loss = max(max_loss, abs(profit))
            else:
                break_even_trades += 1
            
            # 计算持仓天数
            holding_days = (sell.date - buy.date).days
            total_holding_days += holding_days
        
        # 计算胜率和盈亏比
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0
        
        # 计算平均盈利和亏损
        avg_profit = total_profit / winning_trades if winning_trades > 0 else 0
        avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
        
        # 计算平均持仓天数
        avg_holding_days = total_holding_days / total_trades if total_trades > 0 else 0
        
        # 保存统计结果
        self.stats = {
            'initial_cash': initial_cash,
            'final_portfolio_value': final_portfolio_value,
            'total_return': total_return,
            'annual_return': annual_return,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'break_even_trades': break_even_trades,
            'avg_profit': avg_profit,
            'avg_loss': avg_loss,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'avg_holding_days': avg_holding_days
        }
        
        # 保存交易统计
        self.trade_stats = {
            'paired_trades': paired_trades,
            'trades_by_symbol': trades_by_symbol
        }
        
        # 保存投资组合统计
        self.portfolio_stats = {
            'portfolio_value_df': portfolio_value_df,
            'results_by_symbol': results_dict
        }
    
    def get_stats(self):
        """获取绩效统计
        
        Returns:
            dict: 绩效统计字典
        """
        return self.stats
    
    def print_report(self):
        """打印绩效报告"""
        if not self.stats:
            print("没有绩效统计数据")
            return
        
        print("=" * 50)
        print("绩效报告")
        print("=" * 50)
        print(f"初始资金: {self.stats['initial_cash']:.2f}")
        print(f"最终资产: {self.stats['final_portfolio_value']:.2f}")
        print(f"总收益率: {self.stats['total_return']:.2f}%")
        print(f"年化收益率: {self.stats['annual_return']:.2f}%")
        print(f"最大回撤: {self.stats['max_drawdown']:.2f}%")
        print(f"夏普比率: {self.stats['sharpe_ratio']:.2f}")
        print("-" * 50)
        print(f"总交易次数: {self.stats['total_trades']}")
        print(f"盈利交易次数: {self.stats['winning_trades']}")
        print(f"亏损交易次数: {self.stats['losing_trades']}")
        print(f"胜率: {self.stats['win_rate']:.2f}%")
        print(f"盈亏比: {self.stats['profit_factor']:.2f}")
        print("-" * 50)
        print(f"平均盈利: {self.stats['avg_profit']:.2f}")
        print(f"平均亏损: {self.stats['avg_loss']:.2f}")
        print(f"最大盈利: {self.stats['max_profit']:.2f}")
        print(f"最大亏损: {self.stats['max_loss']:.2f}")
        print(f"平均持仓天数: {self.stats['avg_holding_days']:.2f}")
        print("=" * 50)
    
    def plot_equity_curve(self):
        """绘制权益曲线"""
        if not self.portfolio_stats or 'portfolio_value_df' not in self.portfolio_stats:
            print("没有投资组合数据可供绘制")
            return
        
        portfolio_value_df = self.portfolio_stats['portfolio_value_df']
        
        plt.figure(figsize=(12, 6))
        plt.plot(portfolio_value_df.index, portfolio_value_df['total_value'])
        plt.title('投资组合权益曲线')
        plt.xlabel('日期')
        plt.ylabel('价值')
        plt.grid(True)
        plt.tight_layout()
        
        return plt.gcf()
    
    def plot_drawdown(self):
        """绘制回撤曲线"""
        if not self.portfolio_stats or 'portfolio_value_df' not in self.portfolio_stats:
            print("没有投资组合数据可供绘制")
            return
        
        portfolio_value_df = self.portfolio_stats['portfolio_value_df']
        
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
        if not self.portfolio_stats or 'portfolio_value_df' not in self.portfolio_stats:
            print("没有投资组合数据可供绘制")
            return
        
        portfolio_value_df = self.portfolio_stats['portfolio_value_df']
        
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
