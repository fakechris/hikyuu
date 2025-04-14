"""
交易管理模块 - 负责管理交易记录和资金
"""
import pandas as pd
import numpy as np
from datetime import datetime
from enum import Enum


class TradeType(Enum):
    """交易类型枚举"""
    BUY = 1
    SELL = 2
    INIT = 3
    DIVIDEND = 4


class TradeRecord:
    """交易记录类"""
    
    def __init__(self, date, symbol, trade_type, price, shares, commission, slippage, total_cost, cash_change, cash_balance):
        """初始化交易记录
        
        Args:
            date (datetime): 交易日期
            symbol (str): 股票代码
            trade_type (TradeType): 交易类型
            price (float): 交易价格
            shares (float): 交易股数
            commission (float): 佣金
            slippage (float): 滑点成本
            total_cost (float): 总成本
            cash_change (float): 现金变化
            cash_balance (float): 现金余额
        """
        self.date = date
        self.symbol = symbol
        self.trade_type = trade_type
        self.price = price
        self.shares = shares
        self.commission = commission
        self.slippage = slippage
        self.total_cost = total_cost
        self.cash_change = cash_change
        self.cash_balance = cash_balance
    
    def __str__(self):
        """字符串表示"""
        return (f"TradeRecord(date={self.date}, symbol={self.symbol}, "
                f"type={self.trade_type.name}, price={self.price:.2f}, "
                f"shares={self.shares}, cost={self.total_cost:.2f}, "
                f"cash_change={self.cash_change:.2f}, balance={self.cash_balance:.2f})")


class Position:
    """持仓类"""
    
    def __init__(self, symbol, shares=0, avg_price=0.0):
        """初始化持仓
        
        Args:
            symbol (str): 股票代码
            shares (float): 持仓股数
            avg_price (float): 平均成本价
        """
        self.symbol = symbol
        self.shares = shares
        self.avg_price = avg_price
        self.cost_basis = shares * avg_price
    
    def add(self, shares, price):
        """增加持仓
        
        Args:
            shares (float): 增加的股数
            price (float): 买入价格
        """
        if shares <= 0:
            return
        
        # 计算新的平均成本价
        total_cost = self.cost_basis + shares * price
        total_shares = self.shares + shares
        
        self.shares = total_shares
        self.cost_basis = total_cost
        self.avg_price = total_cost / total_shares if total_shares > 0 else 0
    
    def remove(self, shares):
        """减少持仓
        
        Args:
            shares (float): 减少的股数
            
        Returns:
            float: 实际减少的股数
        """
        if shares <= 0:
            return 0
        
        actual_shares = min(shares, self.shares)
        self.shares -= actual_shares
        
        # 如果股数为0，重置平均成本价
        if self.shares == 0:
            self.avg_price = 0
            self.cost_basis = 0
        else:
            self.cost_basis = self.shares * self.avg_price
        
        return actual_shares
    
    def market_value(self, current_price):
        """计算市值
        
        Args:
            current_price (float): 当前价格
            
        Returns:
            float: 市值
        """
        return self.shares * current_price
    
    def profit_loss(self, current_price):
        """计算盈亏
        
        Args:
            current_price (float): 当前价格
            
        Returns:
            float: 盈亏金额
        """
        return self.shares * (current_price - self.avg_price)
    
    def profit_loss_percent(self, current_price):
        """计算盈亏百分比
        
        Args:
            current_price (float): 当前价格
            
        Returns:
            float: 盈亏百分比
        """
        if self.avg_price == 0 or self.shares == 0:
            return 0
        return (current_price - self.avg_price) / self.avg_price * 100
    
    def __str__(self):
        """字符串表示"""
        return (f"Position(symbol={self.symbol}, shares={self.shares}, "
                f"avg_price={self.avg_price:.2f}, cost_basis={self.cost_basis:.2f})")


class TradeCost:
    """交易成本类"""
    
    def __init__(self, commission_rate=0.0003, min_commission=5.0, slippage_rate=0.0001):
        """初始化交易成本
        
        Args:
            commission_rate (float): 佣金率
            min_commission (float): 最低佣金
            slippage_rate (float): 滑点率
        """
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.slippage_rate = slippage_rate
    
    def calculate(self, price, shares):
        """计算交易成本
        
        Args:
            price (float): 交易价格
            shares (float): 交易股数
            
        Returns:
            tuple: (佣金, 滑点成本, 总成本)
        """
        # 计算佣金
        commission = max(price * shares * self.commission_rate, self.min_commission)
        
        # 计算滑点成本
        slippage = price * shares * self.slippage_rate
        
        # 总成本
        total_cost = commission + slippage
        
        return commission, slippage, total_cost


class TradeManager:
    """交易管理类"""
    
    def __init__(self, initial_cash=100000.0, trade_cost=None):
        """初始化交易管理器
        
        Args:
            initial_cash (float): 初始资金
            trade_cost (TradeCost): 交易成本对象
        """
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.trade_cost = trade_cost if trade_cost else TradeCost()
        self.positions = {}  # 持仓字典，键为股票代码，值为Position对象
        self.trade_history = []  # 交易历史记录
        self.daily_portfolio_value = []  # 每日投资组合价值
    
    def buy(self, date, symbol, price, shares=None, amount=None, allow_partial=True):
        """买入操作
        
        Args:
            date (datetime): 交易日期
            symbol (str): 股票代码
            price (float): 买入价格
            shares (float, optional): 买入股数
            amount (float, optional): 买入金额
            allow_partial (bool): 是否允许部分成交
            
        Returns:
            TradeRecord: 交易记录
        """
        if price <= 0:
            raise ValueError("买入价格必须大于0")
        
        # 计算买入股数
        if shares is None and amount is None:
            raise ValueError("必须指定买入股数或买入金额")
        
        if shares is None:
            # 根据金额计算股数，向下取整到100的倍数
            max_shares = amount / price
            shares = int(max_shares / 100) * 100
            if shares == 0 and allow_partial and max_shares >= 1:
                shares = 100  # 至少买入100股
        
        # 计算交易成本
        commission, slippage, total_cost = self.trade_cost.calculate(price, shares)
        
        # 计算总花费
        total_spend = price * shares + total_cost
        
        # 检查资金是否足够
        if total_spend > self.cash:
            if not allow_partial:
                return None  # 资金不足，不允许部分成交
            
            # 计算可买入的最大股数
            max_shares = int((self.cash / (price * (1 + self.trade_cost.commission_rate + self.trade_cost.slippage_rate))) / 100) * 100
            if max_shares == 0:
                return None  # 资金不足以买入最小单位
            
            shares = max_shares
            commission, slippage, total_cost = self.trade_cost.calculate(price, shares)
            total_spend = price * shares + total_cost
        
        # 更新现金
        self.cash -= total_spend
        
        # 更新持仓
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)
        self.positions[symbol].add(shares, price)
        
        # 创建交易记录
        trade_record = TradeRecord(
            date=date,
            symbol=symbol,
            trade_type=TradeType.BUY,
            price=price,
            shares=shares,
            commission=commission,
            slippage=slippage,
            total_cost=total_cost,
            cash_change=-total_spend,
            cash_balance=self.cash
        )
        
        # 添加到交易历史
        self.trade_history.append(trade_record)
        
        return trade_record
    
    def sell(self, date, symbol, price, shares=None, amount=None, percent=None):
        """卖出操作
        
        Args:
            date (datetime): 交易日期
            symbol (str): 股票代码
            price (float): 卖出价格
            shares (float, optional): 卖出股数
            amount (float, optional): 卖出金额
            percent (float, optional): 卖出比例，0-1之间
            
        Returns:
            TradeRecord: 交易记录
        """
        if price <= 0:
            raise ValueError("卖出价格必须大于0")
        
        # 检查是否持有该股票
        if symbol not in self.positions or self.positions[symbol].shares == 0:
            return None
        
        position = self.positions[symbol]
        
        # 计算卖出股数
        if shares is None and amount is None and percent is None:
            # 默认全部卖出
            shares = position.shares
        elif shares is None and amount is not None:
            # 根据金额计算股数
            shares = min(position.shares, int(amount / price / 100) * 100)
            if shares == 0 and amount >= price:
                shares = min(position.shares, 100)  # 至少卖出100股
        elif shares is None and percent is not None:
            # 根据比例计算股数
            if not 0 <= percent <= 1:
                raise ValueError("卖出比例必须在0-1之间")
            shares = int(position.shares * percent / 100) * 100
            if shares == 0 and percent > 0:
                shares = min(position.shares, 100)  # 至少卖出100股
        
        # 确保不超过持有股数
        shares = min(shares, position.shares)
        
        # 计算交易成本
        commission, slippage, total_cost = self.trade_cost.calculate(price, shares)
        
        # 计算总收入
        total_income = price * shares - total_cost
        
        # 更新现金
        self.cash += total_income
        
        # 更新持仓
        position.remove(shares)
        
        # 创建交易记录
        trade_record = TradeRecord(
            date=date,
            symbol=symbol,
            trade_type=TradeType.SELL,
            price=price,
            shares=shares,
            commission=commission,
            slippage=slippage,
            total_cost=total_cost,
            cash_change=total_income,
            cash_balance=self.cash
        )
        
        # 添加到交易历史
        self.trade_history.append(trade_record)
        
        return trade_record
    
    def update_portfolio_value(self, date, price_dict):
        """更新投资组合价值
        
        Args:
            date (datetime): 日期
            price_dict (dict): 价格字典，键为股票代码，值为价格
        """
        # 计算持仓市值
        portfolio_value = self.cash
        positions_value = {}
        
        for symbol, position in self.positions.items():
            if position.shares > 0:
                if symbol in price_dict:
                    price = price_dict[symbol]
                    market_value = position.market_value(price)
                    positions_value[symbol] = market_value
                    portfolio_value += market_value
        
        # 记录每日投资组合价值
        self.daily_portfolio_value.append({
            'date': date,
            'cash': self.cash,
            'positions_value': positions_value,
            'total_value': portfolio_value
        })
    
    def get_position(self, symbol):
        """获取指定股票的持仓
        
        Args:
            symbol (str): 股票代码
            
        Returns:
            Position: 持仓对象
        """
        return self.positions.get(symbol, Position(symbol))
    
    def get_positions(self):
        """获取所有持仓
        
        Returns:
            dict: 持仓字典
        """
        return self.positions
    
    def get_trade_history(self):
        """获取交易历史
        
        Returns:
            list: 交易记录列表
        """
        return self.trade_history
    
    def get_portfolio_value_df(self):
        """获取投资组合价值DataFrame
        
        Returns:
            pd.DataFrame: 投资组合价值DataFrame
        """
        if not self.daily_portfolio_value:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.daily_portfolio_value)
        df.set_index('date', inplace=True)
        return df
    
    def reset(self):
        """重置交易管理器"""
        self.cash = self.initial_cash
        self.positions = {}
        self.trade_history = []
        self.daily_portfolio_value = []
        
        # 添加初始化记录
        init_record = TradeRecord(
            date=datetime.now(),
            symbol='',
            trade_type=TradeType.INIT,
            price=0,
            shares=0,
            commission=0,
            slippage=0,
            total_cost=0,
            cash_change=self.initial_cash,
            cash_balance=self.initial_cash
        )
        self.trade_history.append(init_record)
