# backend/app/api/trading.py
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.services.trade_simulator import TradeSimulator
from app.strategies.base import Order
from pydantic import BaseModel

router = APIRouter(prefix="/trading", tags=["模拟交易"])

# 全局模拟交易实例
simulator = TradeSimulator()

class OrderRequest(BaseModel):
    symbol: str
    direction: str  # BUY/SELL
    price: float
    volume: float
    order_type: str = "MARKET"

@router.post("/start", response_model=dict)
def start_simulation():
    """启动模拟交易"""
    simulator.start()
    return {"status": "started"}

@router.post("/stop", response_model=dict)
def stop_simulation():
    """停止模拟交易"""
    simulator.stop()
    return {"status": "stopped"}

@router.post("/order", response_model=dict)
def submit_order(order: OrderRequest):
    """提交订单"""
    order_obj = Order(
        symbol=order.symbol,
        direction=order.direction,
        price=order.price,
        volume=order.volume,
        order_type=order.order_type
    )
    return simulator.submit_order(order_obj)

@router.get("/account", response_model=dict)
def get_account():
    """获取账户信息"""
    return simulator.get_account_info()

@router.get("/history", response_model=list)
def get_trade_history(limit: int = 100):
    """获取交易历史"""
    return simulator.get_trade_history(limit)