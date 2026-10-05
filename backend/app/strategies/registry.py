# backend/app/strategies/registry.py
from typing import Dict, List, Any, Type
from .base import StrategyBase

# 手动注册列表（也可以改为自动扫描文件夹，但手动注册更可控且安全）
from .dual_ma import DualMaStrategy
from .momentum import MomentumStrategy
from .grid_trading import GridTradingStrategy

class StrategyRegistry:
    _instance = None
    _strategies: Dict[str, Dict[str, Any]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._register_builtin_strategies()
        return cls._instance

    @classmethod
    def _register_builtin_strategies(cls):
        """注册内置策略"""
        strategies_classes = [
            DualMaStrategy,
            MomentumStrategy,
            GridTradingStrategy,  # 网格交易策略
            # 未来新增策略只需在这里添加类名即可
        ]
        
        for strategy_cls in strategies_classes:
            if hasattr(strategy_cls, 'metadata'):
                meta = strategy_cls.metadata
                cls._strategies[meta['id']] = {
                    "id": meta['id'],
                    "name": meta['name'],
                    "description": meta['description'],
                    "params": meta['params'],
                    "class_ref": strategy_cls # 保存类的引用
                }

    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """获取所有策略的元数据（不含代码和类引用，用于前端展示）"""
        return [
            {
                "id": v['id'],
                "name": v['name'],
                "description": v['description'],
                "params": v['params']
            }
            for v in self._strategies.values()
        ]

    def get_strategy_info(self, strategy_id: str) -> Dict[str, Any]:
        """获取单个策略的详细信息"""
        if strategy_id not in self._strategies:
            raise ValueError(f"策略 '{strategy_id}' 不存在")
        info = self._strategies[strategy_id].copy()
        info.pop('class_ref', None) # 移除类引用，避免序列化问题
        return info

    def create_instance(self, strategy_id: str, params: Dict = None) -> StrategyBase:
        """根据 ID 创建策略实例"""
        if strategy_id not in self._strategies:
            raise ValueError(f"策略 '{strategy_id}' 不存在")
        
        strategy_cls = self._strategies[strategy_id]['class_ref']
        return strategy_cls(params)

# 全局单例
registry = StrategyRegistry()