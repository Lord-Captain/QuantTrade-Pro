# backend/app/strategies/base.py
from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import os

# --- 新增：定义订单和持仓类 ---
@dataclass
class Order:
    symbol: str
    direction: str  # 'buy' or 'sell'
    price: float
    volume: int     # 股数
    timestamp: str

@dataclass
class Position:
    symbol: str
    volume: int     # 股数
    avg_price: float

# --- 原有：策略基类 ---
class StrategyBase(ABC):
    """策略基类"""
    
    def __init__(self, params: Optional[Dict] = None):
        self.params = params or {}
        initial_capital_str = os.getenv("INITIAL_CAPITAL", "100000")
        try:
            self.cash = float(initial_capital_str)
        except ValueError:
            # 防止 .env 里填了非数字字符导致崩溃
            print(f"⚠️ 警告：INITIAL_CAPITAL 环境变量格式错误 ('{initial_capital_str}')，使用默认值 100000")
            self.cash = 100000.0
        self.position = 0     # 股数
        self.history = []

    @abstractmethod
    def on_bar(self, date: str, open: float, high: float, low: float, close: float, volume: float) -> Optional[str]:
        pass

    def get_current_asset(self, current_price: float) -> float:
        return self.cash + self.position * current_price