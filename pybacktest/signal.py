"""
信号生成模块 - 负责生成交易信号
"""
import pandas as pd
import numpy as np


class SignalGenerator:
    """信号生成器基类"""
    
    def __init__(self, name="BaseSignal"):
        """初始化信号生成器
        
        Args:
            name (str): 信号生成器名称
        """
        self.name = name
    
    def generate(self, data):
        """生成信号
        
        Args:
            data (pd.DataFrame): 股票数据
            
        Returns:
            pd.DataFrame: 包含信号的DataFrame
        """
        raise NotImplementedError("子类必须实现generate方法")


class CrossSignal(SignalGenerator):
    """均线交叉信号生成器"""
    
    def __init__(self, fast_ma='ma5', slow_ma='ma20', name="CrossSignal"):
        """初始化均线交叉信号生成器
        
        Args:
            fast_ma (str): 快速均线列名
            slow_ma (str): 慢速均线列名
            name (str): 信号生成器名称
        """
        super().__init__(name)
        self.fast_ma = fast_ma
        self.slow_ma = slow_ma
    
    def generate(self, data):
        """生成均线交叉信号
        
        Args:
            data (pd.DataFrame): 股票数据
            
        Returns:
            pd.DataFrame: 包含信号的DataFrame
        """
        df = data.copy()
        
        # 确保均线列存在
        if self.fast_ma not in df.columns:
            raise ValueError(f"数据中不存在快速均线列: {self.fast_ma}")
        if self.slow_ma not in df.columns:
            raise ValueError(f"数据中不存在慢速均线列: {self.slow_ma}")
        
        # 计算金叉和死叉信号
        df['fast_gt_slow'] = df[self.fast_ma] > df[self.slow_ma]
        df['signal'] = 0
        
        # 金叉信号（快线上穿慢线）
        df.loc[(df['fast_gt_slow']) & (~df['fast_gt_slow'].shift(1).fillna(False)), 'signal'] = 1
        
        # 死叉信号（快线下穿慢线）
        df.loc[(~df['fast_gt_slow']) & (df['fast_gt_slow'].shift(1).fillna(False)), 'signal'] = -1
        
        return df


class MACDSignal(SignalGenerator):
    """MACD信号生成器"""
    
    def __init__(self, macd='macd', signal='signal', histogram='histogram', name="MACDSignal"):
        """初始化MACD信号生成器
        
        Args:
            macd (str): MACD列名
            signal (str): 信号线列名
            histogram (str): 柱状图列名
            name (str): 信号生成器名称
        """
        super().__init__(name)
        self.macd = macd
        self.signal = signal
        self.histogram = histogram
    
    def generate(self, data):
        """生成MACD信号
        
        Args:
            data (pd.DataFrame): 股票数据
            
        Returns:
            pd.DataFrame: 包含信号的DataFrame
        """
        df = data.copy()
        
        # 确保MACD列存在
        if self.macd not in df.columns:
            raise ValueError(f"数据中不存在MACD列: {self.macd}")
        if self.signal not in df.columns:
            raise ValueError(f"数据中不存在信号线列: {self.signal}")
        if self.histogram not in df.columns:
            raise ValueError(f"数据中不存在柱状图列: {self.histogram}")
        
        # 计算MACD交叉信号
        df['macd_gt_signal'] = df[self.macd] > df[self.signal]
        df['signal'] = 0
        
        # 金叉信号（MACD上穿信号线）
        df.loc[(df['macd_gt_signal']) & (~df['macd_gt_signal'].shift(1).fillna(False)), 'signal'] = 1
        
        # 死叉信号（MACD下穿信号线）
        df.loc[(~df['macd_gt_signal']) & (df['macd_gt_signal'].shift(1).fillna(False)), 'signal'] = -1
        
        return df


class RSISignal(SignalGenerator):
    """RSI信号生成器"""
    
    def __init__(self, rsi='rsi', overbought=70, oversold=30, name="RSISignal"):
        """初始化RSI信号生成器
        
        Args:
            rsi (str): RSI列名
            overbought (float): 超买阈值
            oversold (float): 超卖阈值
            name (str): 信号生成器名称
        """
        super().__init__(name)
        self.rsi = rsi
        self.overbought = overbought
        self.oversold = oversold
    
    def generate(self, data):
        """生成RSI信号
        
        Args:
            data (pd.DataFrame): 股票数据
            
        Returns:
            pd.DataFrame: 包含信号的DataFrame
        """
        df = data.copy()
        
        # 确保RSI列存在
        if self.rsi not in df.columns:
            raise ValueError(f"数据中不存在RSI列: {self.rsi}")
        
        # 计算RSI信号
        df['signal'] = 0
        
        # 超卖信号（RSI从下向上穿越超卖线）
        df.loc[(df[self.rsi] > self.oversold) & (df[self.rsi].shift(1) <= self.oversold), 'signal'] = 1
        
        # 超买信号（RSI从上向下穿越超买线）
        df.loc[(df[self.rsi] < self.overbought) & (df[self.rsi].shift(1) >= self.overbought), 'signal'] = -1
        
        return df


class BreakoutSignal(SignalGenerator):
    """突破信号生成器"""
    
    def __init__(self, price='close', window=20, name="BreakoutSignal"):
        """初始化突破信号生成器
        
        Args:
            price (str): 价格列名
            window (int): 窗口大小
            name (str): 信号生成器名称
        """
        super().__init__(name)
        self.price = price
        self.window = window
    
    def generate(self, data):
        """生成突破信号
        
        Args:
            data (pd.DataFrame): 股票数据
            
        Returns:
            pd.DataFrame: 包含信号的DataFrame
        """
        df = data.copy()
        
        # 确保价格列存在
        if self.price not in df.columns:
            raise ValueError(f"数据中不存在价格列: {self.price}")
        
        # 计算N日最高价和最低价
        df[f'high_{self.window}'] = df[self.price].rolling(window=self.window).max()
        df[f'low_{self.window}'] = df[self.price].rolling(window=self.window).min()
        
        # 计算突破信号
        df['signal'] = 0
        
        # 向上突破信号
        df.loc[df[self.price] > df[f'high_{self.window}'].shift(1), 'signal'] = 1
        
        # 向下突破信号
        df.loc[df[self.price] < df[f'low_{self.window}'].shift(1), 'signal'] = -1
        
        return df


class CompositeSignal(SignalGenerator):
    """组合信号生成器"""
    
    def __init__(self, signal_generators, weights=None, name="CompositeSignal"):
        """初始化组合信号生成器
        
        Args:
            signal_generators (list): 信号生成器列表
            weights (list, optional): 权重列表，默认为等权重
            name (str): 信号生成器名称
        """
        super().__init__(name)
        self.signal_generators = signal_generators
        
        if weights is None:
            self.weights = [1.0 / len(signal_generators)] * len(signal_generators)
        else:
            if len(weights) != len(signal_generators):
                raise ValueError("权重列表长度必须与信号生成器列表长度相同")
            self.weights = weights
    
    def generate(self, data):
        """生成组合信号
        
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
