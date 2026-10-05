# backend/app/strategies/dual_ma.py
from .base import StrategyBase
from typing import Dict, Optional

from app.utils.logger import get_logger

logger = get_logger(__name__)

class DualMaStrategy(StrategyBase):
    """双均线策略：金叉买入，死叉卖出"""
    
    # 定义策略元数据（供注册中心读取）
    metadata = {
        "id": "dual_ma",
        "name": "双均线策略 (Dual MA)",
        "description": "经典的趋势跟踪策略。当短期均线上穿长期均线时买入，下穿时卖出。",
        "params": [
            {"key": "short_window", "label": "短期均线天数", "type": "int", "min": 2, "max": 60, "default": 5, "step": 1},
            {"key": "long_window", "label": "长期均线天数", "type": "int", "min": 10, "max": 250, "default": 20, "step": 1}
        ]
    }

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(params)
        params = params or {}
        self.short_window = params.get('short_window', 5)
        self.long_window = params.get('long_window', 20)
        self.prices = []

    def on_bar(self, date, open, high, low, close, volume):
        self.prices.append(close)

        if len(self.prices) < self.long_window + 1:
            return None

        short_ma = sum(self.prices[-self.short_window:]) / self.short_window
        long_ma = sum(self.prices[-self.long_window:]) / self.long_window
        prev_short = sum(self.prices[-self.short_window-1:-1]) / self.short_window
        prev_long = sum(self.prices[-self.long_window-1:-1]) / self.long_window

        # 金叉买入
        if prev_short <= prev_long and short_ma > long_ma:
            logger.debug("%s 金叉买入信号: 短均线 %.2f > 长均线 %.2f", date, short_ma, long_ma)
            return 'buy'
        # 死叉卖出
        if prev_short >= prev_long and short_ma < long_ma:
            logger.debug("%s 死叉卖出信号: 短均线 %.2f < 长均线 %.2f", date, short_ma, long_ma)
            return 'sell'

        return None