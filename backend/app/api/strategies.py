# backend/app/api/strategies.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Optional
import importlib.util
import sys

from app.database import get_db
from app.models.strategy import Strategy
from pydantic import BaseModel

router = APIRouter(prefix="/strategies", tags=["策略管理"])

class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    code: str
    parameters: dict = {}

class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    parameters: Optional[dict] = None
    is_active: Optional[bool] = None

@router.post("/", response_model=dict)
def create_strategy(strategy: StrategyCreate, db: Session = Depends(get_db)):
    """创建新策略"""
    db_strategy = Strategy(
        name=strategy.name,
        description=strategy.description,
        code=strategy.code,
        parameters=strategy.parameters
    )
    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return {"id": db_strategy.id, "name": db_strategy.name}

@router.get("/", response_model=List[dict])
def list_strategies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取策略列表"""
    strategies = db.query(Strategy).offset(skip).limit(limit).all()
    return [{
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "parameters": s.parameters,
        "is_active": s.is_active,
        "created_at": s.created_at
    } for s in strategies]

@router.get("/{strategy_id}", response_model=dict)
def get_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """获取策略详情"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "code": strategy.code,
        "parameters": strategy.parameters,
        "is_active": strategy.is_active
    }

@router.put("/{strategy_id}", response_model=dict)
def update_strategy(strategy_id: int, strategy: StrategyUpdate, db: Session = Depends(get_db)):
    """更新策略"""
    db_strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not db_strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    update_data = strategy.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_strategy, key, value)
    
    db.commit()
    db.refresh(db_strategy)
    return {"id": db_strategy.id, "name": db_strategy.name}

@router.delete("/{strategy_id}", response_model=dict)
def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    """删除策略"""
    db_strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not db_strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    db.delete(db_strategy)
    db.commit()
    return {"message": "策略已删除"}


