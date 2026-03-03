# backend/app/strategies/dual_ma.py
from .base import StrategyBase
from typing import Dict, Optional

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
        self.short_window = params.get('short_window', 5)
        self.long_window = params.get('long_window', 20)
        self.prices = []

    def on_bar(self, date, open, high, low, close, volume):
        self.prices.append(close)
        
        # 调试：每10天打印一次内部状态
        if len(self.prices) % 10 == 0 or len(self.prices) < self.long_window + 2:
            print(f"  🧮 [{date}] 价格队列长度:{len(self.prices)}, 当前价:{close:.2f}, 需要>{self.long_window}才启动")

        if len(self.prices) < self.long_window:
            return None
        
        short_ma = sum(self.prices[-self.short_window:]) / self.short_window
        long_ma = sum(self.prices[-self.long_window:]) / self.long_window
        
        # 调试：打印均线值
        if len(self.prices) >= self.long_window:
             # 避免日志太多，只在刚开始满足条件时打印几次
             if len(self.prices) <= self.long_window + 5:
                 print(f"  📈 [{date}] 短均线({self.short_window}日):{short_ma:.2f}, 长均线({self.long_window}日):{long_ma:.2f}")

        # 防止索引错误
        if len(self.prices) < self.long_window + 1:
            return None
            
        prev_short = sum(self.prices[-self.short_window-1:-1]) / self.short_window
        prev_long = sum(self.prices[-self.long_window-1:-1]) / self.long_window
        
        # 金叉买入
        if prev_short <= prev_long and short_ma > long_ma:
            print(f"  ✅ [{date}] 触发金叉买入信号！短:{short_ma:.2f} > 长:{long_ma:.2f}")
            return 'buy'
        # 死叉卖出
        elif prev_short >= prev_long and short_ma < long_ma:
            print(f"  ❌ [{date}] 触发死叉卖出信号！短:{short_ma:.2f} < 长:{long_ma:.2f}")
            return 'sell'
        
        return None