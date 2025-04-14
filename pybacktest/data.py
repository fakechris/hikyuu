"""
数据管理模块 - 负责加载和处理历史数据
"""
import pandas as pd
import numpy as np
from datetime import datetime
import os


class DataHandler:
    """数据处理类，负责加载和管理历史数据"""
    
    def __init__(self):
        self.data = {}  # 存储所有股票数据的字典
        
    def load_csv(self, symbol, filepath, date_format='%Y-%m-%d'):
        """从CSV文件加载数据
        
        Args:
            symbol (str): 股票代码
            filepath (str): CSV文件路径
            date_format (str): 日期格式
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        
        # 读取CSV文件
        df = pd.read_csv(filepath)
        
        # 确保必要的列存在
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"CSV文件缺少必要的列: {col}")
        
        # 转换日期列
        df['date'] = pd.to_datetime(df['date'], format=date_format)
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        # 确保所有价格列是数值类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 计算常用的技术指标
        self._calculate_indicators(df)
        
        # 存储数据
        self.data[symbol] = df
        
        return df
    
    def load_dataframe(self, symbol, dataframe):
        """从DataFrame加载数据
        
        Args:
            symbol (str): 股票代码
            dataframe (pd.DataFrame): 包含OHLCV数据的DataFrame
        """
        df = dataframe.copy()
        
        # 确保必要的列存在
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in df.columns:
                raise ValueError(f"DataFrame缺少必要的列: {col}")
        
        # 确保索引是日期类型
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame的索引必须是DatetimeIndex类型")
        
        # 确保所有价格列是数值类型
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # 计算常用的技术指标
        self._calculate_indicators(df)
        
        # 存储数据
        self.data[symbol] = df
        
        return df
    
    def get_data(self, symbol, start_date=None, end_date=None):
        """获取指定股票的数据
        
        Args:
            symbol (str): 股票代码
            start_date (str or datetime, optional): 开始日期
            end_date (str or datetime, optional): 结束日期
            
        Returns:
            pd.DataFrame: 股票数据
        """
        if symbol not in self.data:
            raise KeyError(f"数据中不存在股票: {symbol}")
        
        df = self.data[symbol]
        
        if start_date is not None:
            if isinstance(start_date, str):
                start_date = pd.to_datetime(start_date)
            df = df[df.index >= start_date]
        
        if end_date is not None:
            if isinstance(end_date, str):
                end_date = pd.to_datetime(end_date)
            df = df[df.index <= end_date]
        
        return df
    
    def _calculate_indicators(self, df):
        """计算常用技术指标
        
        Args:
            df (pd.DataFrame): 股票数据
        """
        # 计算移动平均线
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()
        df['ma60'] = df['close'].rolling(window=60).mean()
        
        # 计算MACD
        df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema12'] - df['ema26']
        df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['histogram'] = df['macd'] - df['signal']
        
        # 计算RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df
    
    def generate_signals(self, symbol, signal_func):
        """根据信号生成函数生成交易信号
        
        Args:
            symbol (str): 股票代码
            signal_func (function): 信号生成函数，接收DataFrame作为参数，返回包含信号的DataFrame
            
        Returns:
            pd.DataFrame: 包含交易信号的DataFrame
        """
        if symbol not in self.data:
            raise KeyError(f"数据中不存在股票: {symbol}")
        
        df = self.data[symbol].copy()
        df = signal_func(df)
        
        return df
