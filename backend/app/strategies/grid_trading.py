from typing import Dict, Optional
from .base import StrategyBase


class GridTradingStrategy(StrategyBase):
    """
    网格交易策略：围绕基准价格按固定百分比划分价格网格，
    价格每下跌一个网格买入一笔，价格每上涨一个网格卖出一笔，实现高抛低吸。
    """

    metadata = {
        "id": "grid",
        "name": "网格交易策略 (Grid)",
        "description": "围绕初始价格等距划分网格，价格下跌买入、上涨卖出，实现高抛低吸。",
        "params": [
            {
                "key": "grid_size",
                "label": "单格间距 (%)",
                "type": "float",
                "min": 0.5,
                "max": 10.0,
                "default": 2.0,
                "step": 0.5,
            },
            {
                "key": "max_grid",
                "label": "最大网格层数",
                "type": "int",
                "min": 3,
                "max": 30,
                "default": 10,
                "step": 1,
            },
        ],
    }

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(params)
        params = params or {}
        # 单格间距百分比，例如 2% -> 0.02
        self.grid_size_pct: float = float(params.get("grid_size", 2.0)) / 100.0
        if self.grid_size_pct <= 0:
            self.grid_size_pct = 0.02

        self.max_grid: int = int(params.get("max_grid", 10))
        if self.max_grid <= 0:
            self.max_grid = 10

        self.base_price: Optional[float] = None
        self.last_grid_level: int = 0

    def _get_grid_level(self, price: float) -> int:
        """
        根据当前价格计算所属网格层级：
        level = round((price - base_price) / (base_price * grid_size_pct))
        """
        if self.base_price is None or self.grid_size_pct <= 0:
            return 0

        offset = (price - self.base_price) / (self.base_price * self.grid_size_pct)
        level = int(round(offset))

        # 限制在 [-max_grid, max_grid] 范围内，避免极端价格导致过大网格编号
        if level > self.max_grid:
            level = self.max_grid
        elif level < -self.max_grid:
            level = -self.max_grid

        return level

    def on_bar(
        self,
        date: str,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float,
    ) -> Optional[str]:
        # 第一天记录基准价格，不交易
        if self.base_price is None:
            self.base_price = close
            self.last_grid_level = 0
            return None

        current_level = self._get_grid_level(close)
        delta = current_level - self.last_grid_level

        # 价格下跌到更低的网格：买入一笔
        if delta <= -1:
            self.last_grid_level = current_level
            return "buy"

        # 价格上涨到更高的网格：若有持仓则卖出一笔
        if delta >= 1 and self.position > 0:
            self.last_grid_level = current_level
            return "sell"

        return None

