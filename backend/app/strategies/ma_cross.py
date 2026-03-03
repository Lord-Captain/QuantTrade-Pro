# strategies/ma_cross.py - 均线交叉策略
from app.strategies.base import BaseStrategy, Signal, Order
import pandas as pd
import numpy as np

class MACrossStrategy(BaseStrategy):
    """均线交叉策略"""
    
    def __init__(self, name="MA Cross", parameters=None):
        super().__init__(name, parameters)
        self.short_period = parameters.get("short_period", 5)
        self.long_period = parameters.get("long_period", 20)
        self.volume = parameters.get("volume", 100)
        
        self.short_ma = None
        self.long_ma = None
        self.prev_short_ma = None
        self.prev_long_ma = None
    
    def initialize(self, data: pd.DataFrame) -> None:
        """初始化策略"""
        data['short_ma'] = data['close'].rolling(window=self.short_period).mean()
        data['long_ma'] = data['close'].rolling(window=self.long_period).mean()
        self.short_ma = data['short_ma']
        self.long_ma = data['long_ma']
    
    def on_bar(self, bar: dict) -> Order:
        """处理每根K线"""
        current_price = bar.get('close')
        symbol = bar.get('symbol')
        
        # 获取当前 MA 值
        current_short = self.short_ma.iloc[-1] if hasattr(self.short_ma, 'iloc') else current_price
        current_long = self.long_ma.iloc[-1] if hasattr(self.long_ma, 'iloc') else current_price
        
        # 金叉：短均线上穿长均线
        if self.prev_short_ma and self.prev_long_ma:
            if self.prev_short_ma <= self.prev_long_ma and current_short > current_long:
                # 买入信号
                return Order(
                    symbol=symbol,
                    direction="BUY",
                    price=current_price,
                    volume=self.volume
                )
            
            # 死叉：短均线下穿长均线
            elif self.prev_short_ma >= self.prev_long_ma and current_short < current_long:
                # 卖出信号
                position = self.get_position(symbol)
                if position:
                    return Order(
                        symbol=symbol,
                        direction="SELL",
                        price=current_price,
                        volume=position.volume
                    )
        
        # 更新前值
        self.prev_short_ma = current_short
        self.prev_long_ma = current_long
        
        return None