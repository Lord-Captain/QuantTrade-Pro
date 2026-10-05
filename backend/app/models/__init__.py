# backend/app/models/__init__.py
from app.database import Base

# 1. 首先导入 strategy 模块 (定义 Strategy 类)
# 此时 Strategy 类被创建并注册到 Base.registry
from app.models import strategy

# 2. 接着导入 backtest 模块
# 此时 BacktestResult 被创建，并尝试解析 "Strategy"。
# 因为 strategy 模块已加载，Strategy 已在 registry 中，所以解析成功。
from app.models import backtest

# 3. 最后导入 trade 模块
# 此时 SimulatedTrade 被创建，并尝试解析 "Strategy"。
# 因为 strategy 模块早已加载，所以解析成功。
from app.models import trade

# 4. 导出类供外部使用
from app.models.strategy import Strategy
from app.models.backtest import BacktestResult
from app.models.trade import SimulatedTrade

__all__ = ["Base", "Strategy", "BacktestResult", "SimulatedTrade"]