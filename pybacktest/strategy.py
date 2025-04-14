"""
策略模块 - 负责实现交易策略
"""
import pandas as pd
import numpy as np
from datetime import datetime
from .signal import SignalGenerator
from .trade import TradeManager, TradeType


class Strategy:
    """策略基类"""
    
    def __init__(self, name="BaseStrategy"):
        """初始化策略
        
        Args:
            name (str): 策略名称
        """
        self.name = name
    
    def generate_signals(self, data):
        """生成交易信号
        
        Args:
            data (pd.DataFrame): 股票数据
            
        Returns:
            pd.DataFrame: 包含信号的DataFrame
        """
        raise NotImplementedError("子类必须实现generate_signals方法")
    
    def run(self, data, trade_manager, **kwargs):
        """运行策略
        
        Args:
            data (pd.DataFrame): 股票数据
            trade_manager (TradeManager): 交易管理器
            
        Returns:
            pd.DataFrame: 包含交易信号和结果的DataFrame
        """
        raise NotImplementedError("子类必须实现run方法")


class SignalStrategy(Strategy):
    """基于信号的策略"""
    
    def __init__(self, signal_generator, symbol, name="SignalStrategy"):
        """初始化基于信号的策略
        
        Args:
            signal_generator (SignalGenerator): 信号生成器
            symbol (str): 股票代码
            name (str): 策略名称
        """
        super().__init__(name)
        self.signal_generator = signal_generator
        self.symbol = symbol
    
    def generate_signals(self, data):
        """生成交易信号
        
        Args:
            data (pd.DataFrame): 股票数据
            
        Returns:
            pd.DataFrame: 包含信号的DataFrame
        """
        return self.signal_generator.generate(data)
    
    def run(self, data, trade_manager, initial_cash=None, position_size=None, position_pct=None):
        """运行策略
        
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
            
            # 根据信号执行交易
            if row['signal'] == 1:  # 买入信号
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
            
            elif row['signal'] == -1:  # 卖出信号
                # 如果有持仓，全部卖出
                if position.shares > 0:
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
            
            # 更新投资组合价值
            trade_manager.update_portfolio_value(
                date=current_date,
                price_dict={self.symbol: current_price}
            )
        
        return df


class MultiSignalStrategy(Strategy):
    """多信号策略"""
    
    def __init__(self, signal_generators, symbol, weights=None, name="MultiSignalStrategy"):
        """初始化多信号策略
        
        Args:
            signal_generators (list): 信号生成器列表
            symbol (str): 股票代码
            weights (list, optional): 权重列表，默认为等权重
            name (str): 策略名称
        """
        super().__init__(name)
        self.signal_generators = signal_generators
        self.symbol = symbol
        
        if weights is None:
            self.weights = [1.0 / len(signal_generators)] * len(signal_generators)
        else:
            if len(weights) != len(signal_generators):
                raise ValueError("权重列表长度必须与信号生成器列表长度相同")
            self.weights = weights
    
    def generate_signals(self, data):
        """生成交易信号
        
        Args:
            data (pd.DataFrame): 股票数据
            
        Returns:
            pd.DataFrame: 包含信号的DataFrame
        """
        df = data.copy()
        df['signal'] = 0
        
        # 生成各个信号
        for i, generator in enumerate(self.signal_generators):
            signal_df = generator.generate(df)
            df[f'signal_{i}'] = signal_df['signal']
        
        # 计算加权信号
        for i in range(len(self.signal_generators)):
            df['signal'] += df[f'signal_{i}'] * self.weights[i]
        
        # 信号阈值处理
        df['signal_threshold'] = 0
        df.loc[df['signal'] > 0.5, 'signal_threshold'] = 1
        df.loc[df['signal'] < -0.5, 'signal_threshold'] = -1
        
        # 使用阈值信号作为最终信号
        df['signal'] = df['signal_threshold']
        
        return df
    
    def run(self, data, trade_manager, initial_cash=None, position_size=None, position_pct=None):
        """运行策略
        
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
            
            # 根据信号执行交易
            if row['signal'] == 1:  # 买入信号
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
            
            elif row['signal'] == -1:  # 卖出信号
                # 如果有持仓，全部卖出
                if position.shares > 0:
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
            
            # 更新投资组合价值
            trade_manager.update_portfolio_value(
                date=current_date,
                price_dict={self.symbol: current_price}
            )
        
        return df


class PortfolioStrategy(Strategy):
    """投资组合策略"""
    
    def __init__(self, strategies, name="PortfolioStrategy"):
        """初始化投资组合策略
        
        Args:
            strategies (dict): 策略字典，键为股票代码，值为策略对象
            name (str): 策略名称
        """
        super().__init__(name)
        self.strategies = strategies
    
    def run(self, data_dict, trade_manager, initial_cash=None, position_pct=None):
        """运行投资组合策略
        
        Args:
            data_dict (dict): 数据字典，键为股票代码，值为DataFrame
            trade_manager (TradeManager): 交易管理器
            initial_cash (float, optional): 初始资金，如果提供则重置交易管理器
            position_pct (float or dict, optional): 每只股票的资金比例，可以是单一值或字典
            
        Returns:
            dict: 包含每只股票交易结果的字典
        """
        # 如果提供了初始资金，重置交易管理器
        if initial_cash is not None:
            trade_manager.reset()
        
        # 确保数据字典和策略字典的键一致
        for symbol in self.strategies:
            if symbol not in data_dict:
                raise ValueError(f"数据字典中缺少股票: {symbol}")
        
        # 处理资金比例
        if position_pct is None:
            # 默认平均分配资金
            position_pct_dict = {symbol: 1.0 / len(self.strategies) for symbol in self.strategies}
        elif isinstance(position_pct, dict):
            position_pct_dict = position_pct
        else:
            # 使用相同的资金比例
            position_pct_dict = {symbol: position_pct for symbol in self.strategies}
        
        # 运行每个策略
        results = {}
        for symbol, strategy in self.strategies.items():
            data = data_dict[symbol]
            
            # 计算该股票的资金比例
            symbol_position_pct = position_pct_dict.get(symbol, 1.0 / len(self.strategies))
            
            # 运行策略
            result_df = strategy.run(
                data=data,
                trade_manager=trade_manager,
                position_pct=symbol_position_pct
            )
            
            results[symbol] = result_df
        
        return results
