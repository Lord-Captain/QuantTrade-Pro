# backend/app/api/market.py
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/market", tags=["市场行情"])

@router.get("/overview")
def get_market_overview():
    return {"status": "normal", "message": "市场数据服务正常"}