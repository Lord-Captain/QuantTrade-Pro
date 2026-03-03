# backend/app/api/data.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.services.data_manager import DataManager

# ... 原有导入 ...
from app.services.data_sources.factory import factory
from pydantic import BaseModel

router = APIRouter(prefix="/data", tags=["数据管理"])

@router.get("/realtime/{symbol}")
def get_realtime_data(symbol: str):
    """获取实时数据 - 兼容多种格式"""
    print(f"--- [API] 接收到实时数据请求: {symbol} ---")
    
    # 1. 清洗代码
    clean_symbol = symbol.strip().lower()
    if clean_symbol.startswith("sh") or clean_symbol.startswith("sz"):
        clean_symbol = clean_symbol[2:]
    
    print(f"--- [API] 清洗后代码: {clean_symbol} ---")

    try:
        dm = DataManager()
        # 调用服务层
        result = dm.get_realtime_data(clean_symbol)
        
        if not result:
            print(f"--- [API] 未获取到数据 ---")
            # 返回友好提示，而不是 404，方便前端处理
            return {
                "success": False,
                "message": f"无法获取代码 {clean_symbol} 的实时数据，请检查代码是否正确或市场是否开盘",
                "symbol": clean_symbol
            }
        # 【新增】成功获取数据后，立即检查并打印工厂状态
        from app.services.data_sources.factory import factory
        current = factory.get_current_source()
        print(f"✅ [API 确认] 数据获取成功。当前工厂状态 -> 模式：{'自动' if factory.auto_switch_enabled else '手动'}, 实际使用源：{current.name}")
        #print(f"--- [API] 成功获取数据 ---")
        return {"success": True, "data": result}
        
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"--- [API] 发生异常: {error_msg} ---")
        print(traceback.format_exc())
        
        # 如果是 AkShare 的特定错误，可以捕获得更细致
        raise HTTPException(status_code=500, detail=f"数据服务内部错误: {error_msg}")


class SourceSwitchRequest(BaseModel):
    mode: str  # "auto" or "manual"
    source_name: Optional[str] = None # 手动模式时需要

@router.get("/source/status")
def get_source_status():
    """获取当前数据源状态"""
    current = factory.get_current_source()
    return {
        "mode": "auto" if factory.auto_switch_enabled else "manual",
        "current_source": current.name,
        "available_sources": factory.get_available_sources()
    }

@router.post("/source/switch")
def switch_source(req: SourceSwitchRequest):
    if req.mode == "auto":
        factory.set_auto_mode(True)
        return {"message": "已切换到自动模式", "mode": "auto"}
    
    elif req.mode == "manual":
        # 手动模式必须提供 source_name
        if not req.source_name:
            # 返回更友好的错误信息
            raise HTTPException(status_code=400, detail="手动模式必须指定 source_name 参数")
        
        try:
            factory.set_manual_source(req.source_name)
            return {"message": f"已锁定数据源：{req.source_name}", "mode": "manual"}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    raise HTTPException(status_code=400, detail="无效的 mode 参数")