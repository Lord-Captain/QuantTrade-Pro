# backend/app/models/trade.py
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

# 【关键】必须从 app.database 导入 Base，确保所有模型共用同一个 registry
from app.database import Base 

class SimulatedTrade(Base):
    __tablename__ = "simulated_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True) # 允许为空以防万一
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10))  # BUY/SELL
    price = Column(Float)
    volume = Column(Float)
    filled_price = Column(Float)
    commission = Column(Float)
    status = Column(String(20), default="PENDING")
    pnl = Column(Float, default=0.0)
    order_time = Column(DateTime, default=datetime.utcnow)
    fill_time = Column(DateTime)
    
    # 【关键】使用字符串 "Strategy"
    # 如果不需要在 Strategy 类中反向访问 trades 列表，可以不加 back_populates，或者只加 backref
    # 这里我们使用 backref 自动在 Strategy 上创建一个 'trades' 属性，避免在 Strategy 类中再写一遍 relationship
    strategy = relationship("Strategy", backref="trades")