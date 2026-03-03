# backend/app/models/strategy.py
from sqlalchemy import Column, Integer, String, Text, JSON, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

# 【关键】统一从 app.database 导入 Base
from app.database import Base

class Strategy(Base):
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    code = Column(Text, nullable=False)
    description = Column(Text)
    parameters = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 只保留对 BacktestResult 的关系
    # 注意：这里不要定义 trades 关系，因为 trade.py 里的 backref="trades" 会自动处理
    backtests = relationship("BacktestResult", back_populates="strategy", cascade="all, delete-orphan")