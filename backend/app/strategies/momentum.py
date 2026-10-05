# backend/app/strategies/momentum.py
from .base import StrategyBase
from typing import Dict, Optional

class MomentumStrategy(StrategyBase):
    """动量突破策略：突破 N 日高点买入，止损或跌破低点卖出"""
    
    metadata = {
        "id": "momentum",
        "name": "动量突破策略 (Momentum)",
        "description": "基于过去 N 天的最高价突破进行买入，跌破最低价或触发止损时卖出。",
        "params": [
            {"key": "lookback", "label": "观察期天数", "type": "int", "min": 5, "max": 60, "default": 20, "step": 1},
            {"key": "stop_loss", "label": "止损比例 (%)", "type": "float", "min": 1.0, "max": 20.0, "default": 5.0, "step": 0.5}
        ]
    }

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(params)
        params = params or {}
        self.lookback = params.get('lookback', 20)
        stop_loss = float(params.get('stop_loss', 0.05))
        # 兼容百分数（5.0 表示 5%）与小数（0.05）两种写法，统一转为小数
        self.stop_loss = stop_loss / 100 if stop_loss > 1 else stop_loss
        self.prices = []
        self.entry_price = 0.0

    def on_bar(self, date: str, open: float, high: float, low: float, close: float, volume: float) -> Optional[str]:
        self.prices.append(close)
        if len(self.prices) < self.lookback + 1:
            return None
        
        highest = max(self.prices[-self.lookback-1:-1])
        lowest = min(self.prices[-self.lookback-1:-1])
        
        if self.position == 0:
            if close > highest:
                self.entry_price = close
                return 'buy'
        else:
            # 止损
            if close < self.entry_price * (1 - self.stop_loss):
                return 'sell'
            # 止盈/反转
            if close < lowest:
                return 'sell'
        return None