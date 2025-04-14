"""
PyBacktest - 一个纯Python实现的回测引擎
"""

from .data import DataHandler
from .trade import TradeManager, TradeCost, TradeRecord, Position, TradeType
from .signal import SignalGenerator, CrossSignal, MACDSignal, RSISignal, BreakoutSignal, CompositeSignal
from .strategy import Strategy, SignalStrategy, MultiSignalStrategy, PortfolioStrategy
from .backtest import Backtest
from .performance import Performance

__version__ = '0.1.0'
__author__ = 'PyBacktest Team'
