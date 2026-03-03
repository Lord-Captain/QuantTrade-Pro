# backend/app/api/backtest.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from app.services.backtest_engine import BacktestEngine
from app.strategies.registry import registry

router = APIRouter(prefix="/backtest", tags=["回测管理"])

class BacktestRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    strategy_id: str
    params: Dict[str, Any]

@router.get("/strategies")
def get_strategies():
    """获取策略列表（用于前端下拉框）"""
    return registry.get_all_strategies()

@router.post("/run")
def run_backtest(req: BacktestRequest):
    """运行回测"""
    try:
        # 1. 验证策略是否存在并获取类（通过注册中心）
        # 这里不需要获取代码字符串了，直接让引擎使用类实例，或者传递类给引擎
        # 为了兼容现有的 BacktestEngine (它接受代码字符串)，我们可以稍微调整一下引擎，
        # 或者更优雅地：修改 BacktestEngine.run 方法，让它支持直接传入策略实例。
        
        # 【方案 A：修改引擎以支持实例】<- 推荐，更安全高效
        engine = BacktestEngine()
        
        # 创建策略实例
        strategy_instance = registry.create_instance(req.strategy_id, req.params)
        
        result = engine.run_with_instance(
            symbol=req.symbol,
            start_date=req.start_date,
            end_date=req.end_date,
            strategy_instance=strategy_instance
        )
        
        return {"success": True, "data": result}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))