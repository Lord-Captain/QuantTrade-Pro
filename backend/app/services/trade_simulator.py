from typing import Dict, List, Optional, Any
from datetime import datetime
import json

from .backtest_engine import BacktestEngine
from app.strategies.base import Order, Position

class TradeSimulator:
    """模拟交易引擎"""
    
    def __init__(
        self,
        initial_capital: float = 1000000.0,
        commission_rate: float = 0.0003
    ):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.commission_rate = commission_rate
        
        self.positions: Dict[str, Position] = {}
        self.orders: List[Dict] = []
        self.trade_history: List[Dict] = []
        self.is_running = False
    
    def start(self) -> bool:
        """启动模拟交易"""
        self.is_running = True
        return True
    
    def stop(self) -> bool:
        """停止模拟交易"""
        self.is_running = False
        return True
    
    def submit_order(self, order: Order) -> Dict:
        """提交订单"""
        if not self.is_running:
            return {"status": "error", "message": "模拟交易未启动"}
        
        order_id = len(self.orders) + 1
        order_dict = {
            "order_id": order_id,
            "symbol": order.symbol,
            "direction": order.direction,
            "price": order.price,
            "volume": order.volume,
            "order_type": order.order_type,
            "status": "PENDING",
            "submit_time": datetime.now().isoformat()
        }
        
        self.orders.append(order_dict)
        
        # 模拟立即成交
        self._execute_order(order_dict)
        
        return {"status": "success", "order_id": order_id}
    
    def _execute_order(self, order: Dict) -> None:
        """执行订单"""
        fill_price = order["price"]
        commission = fill_price * order["volume"] * self.commission_rate
        
        if order["direction"] == "BUY":
            cost = fill_price * order["volume"] + commission
            if cost <= self.capital:
                self.capital -= cost
                
                if order["symbol"] in self.positions:
                    pos = self.positions[order["symbol"]]
                    total_volume = pos["volume"] + order["volume"]
                    avg_price = (pos["avg_price"] * pos["volume"] + fill_price * order["volume"]) / total_volume
                    pos["volume"] = total_volume
                    pos["avg_price"] = avg_price
                else:
                    self.positions[order["symbol"]] = {
                        "symbol": order["symbol"],
                        "volume": order["volume"],
                        "avg_price": fill_price
                    }
                
                order["status"] = "FILLED"
                order["fill_price"] = fill_price
                order["fill_time"] = datetime.now().isoformat()
                order["commission"] = commission
                
                self.trade_history.append({
                    "type": "BUY",
                    "symbol": order["symbol"],
                    "price": fill_price,
                    "volume": order["volume"],
                    "commission": commission,
                    "time": order["fill_time"]
                })
        
        elif order["direction"] == "SELL":
            if order["symbol"] in self.positions:
                pos = self.positions[order["symbol"]]
                sell_volume = min(order["volume"], pos["volume"])
                
                if sell_volume > 0:
                    revenue = fill_price * sell_volume - commission
                    self.capital += revenue
                    
                    pnl = (fill_price - pos["avg_price"]) * sell_volume - commission
                    
                    pos["volume"] -= sell_volume
                    if pos["volume"] <= 0:
                        del self.positions[order["symbol"]]
                    
                    order["status"] = "FILLED"
                    order["fill_price"] = fill_price
                    order["fill_time"] = datetime.now().isoformat()
                    order["commission"] = commission
                    order["pnl"] = pnl
                    
                    self.trade_history.append({
                        "type": "SELL",
                        "symbol": order["symbol"],
                        "price": fill_price,
                        "volume": sell_volume,
                        "commission": commission,
                        "pnl": pnl,
                        "time": order["fill_time"]
                    })
    
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        position_value = sum(
            pos["volume"] * pos["avg_price"] 
            for pos in self.positions.values()
        )
        
        return {
            "capital": self.capital,
            "position_value": position_value,
            "total_equity": self.capital + position_value,
            "positions": list(self.positions.values()),
            "pending_orders": [o for o in self.orders if o["status"] == "PENDING"],
            "trade_count": len(self.trade_history)
        }
    
    def get_trade_history(self, limit: int = 100) -> List[Dict]:
        """获取交易历史"""
        return self.trade_history[-limit:]