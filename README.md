# QuantTrade Pro - 量化交易全栈平台

一个前后端分离的量化交易系统，支持 **A 股实时行情接入、策略回测、模拟交易与策略管理**。内置多数据源自动降级、本地数据缓存、含手续费/滑点的撮合引擎，以及完整的绩效指标体系（夏普比率、年化收益、最大回撤、胜率等）。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12 · FastAPI · SQLAlchemy · Pydantic v2 · Pandas |
| 前端 | Vue 3 · Vite · Vue Router |
| 数据 | SQLite（持久化）· CSV 本地缓存 · Tushare / 新浪财经 / AkShare |
| 部署 | Docker · Docker Compose |
| 测试 | pytest（24 个单元/端到端测试） |

## 系统架构

```
┌─────────────────────┐        HTTP/REST        ┌──────────────────────────────┐
│  Frontend (Vue 3)   │ ───────────────────────▶│  Backend (FastAPI)           │
│  回测/行情/交易视图  │                         │  ┌────────────────────────┐  │
└─────────────────────┘                         │  │ API Layer (api/v1)     │  │
                                                │  └──────────┬─────────────┘  │
                                                │  ┌──────────▼─────────────┐  │
                                                │  │ Service Layer          │  │
                                                │  │ ├ BacktestEngine       │  │
                                                │  │ │  逐bar撮合+手续费/滑点│  │
                                                │  │ ├ TradeSimulator       │  │
                                                │  │ └ DataManager (CSV缓存)│  │
                                                │  └──────────┬─────────────┘  │
                                                │  ┌──────────▼─────────────┐  │
                                                │  │ DataSourceFactory      │  │
                                                │  │ Tushare→Sina→AkShare   │  │
                                                │  │ 故障自动降级 + 懒加载    │  │
                                                │  └────────────────────────┘  │
                                                │  StrategyRegistry (策略插件化)│
                                                └──────────────────────────────┘
```

## 核心设计

- **策略插件化（策略模式 + 注册中心）**：策略继承 `StrategyBase` 并实现 `on_bar()`，通过 `metadata` 声明参数 schema，注册中心自动暴露给前端渲染参数表单，新增策略无需修改任何现有代码（开闭原则）。
- **多数据源容灾（工厂模式）**：Tushare → Sina → AkShare 按优先级自动降级切换，记录最近成功源避免重复探测；数据源依赖懒加载，单个源的第三方库缺失不影响系统启动。
- **真实感回测引擎**：逐 bar 事件驱动撮合，计入**手续费（万三）与滑点**，按 A 股整手（100 股）交易，输出夏普比率、年化收益率、最大回撤、胜率、基准（买入持有）对比曲线。
- **本地缓存层**：历史行情按 `标的_起止日期` 落盘 CSV，重复回测零网络开销。
- **统一日志体系**：控制台 + 滚动文件持久化（RotatingFileHandler），按模块分级。

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
docker compose up -d
# 前端: http://localhost    后端 API 文档: http://localhost:8000/docs
```

### 方式二：本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
# 可选：在 backend/.env 中配置 TUSHARE_TOKEN（不配置则自动降级到其他数据源）
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### 运行测试

```bash
cd backend
python -m pytest tests -v
```

## 内置策略

| 策略 | 说明 | 可调参数 |
|---|---|---|
| 双均线 (dual_ma) | 短期均线上穿长期均线买入（金叉），下穿卖出（死叉） | 短/长均线周期 |
| 动量突破 (momentum) | 突破 N 日高点买入，跌破 N 日低点或触发止损卖出 | 观察期、止损比例 |
| 网格交易 (grid) | 围绕基准价等距划格，跌一格买、涨一格卖，高抛低吸 | 网格间距、最大层数 |

## API 一览

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/backtest/strategies` | 获取策略列表及参数 schema |
| POST | `/api/v1/backtest/run` | 运行回测，返回资金曲线与绩效指标 |
| GET | `/api/v1/market/realtime/{symbol}` | 实时行情（多源自动降级） |
| GET | `/api/v1/data/sources` | 数据源状态查询与切换 |
| POST | `/api/v1/trading/order` | 模拟交易下单 |
| GET | `/health` | 健康检查 |

回测响应示例（节选）：

```json
{
  "total_return": 18.35,
  "benchmark_return": 6.12,
  "annualized_return": 15.87,
  "max_drawdown": 8.42,
  "sharpe_ratio": 1.26,
  "win_rate": 62.5,
  "trades": [...], "capital_curve": [...], "benchmark_curve": [...]
}
```

## 环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `TUSHARE_TOKEN` | Tushare Pro API Token（可选） | 空（自动降级） |
| `INITIAL_CAPITAL` | 回测初始资金 | `100000` |
| `COMMISSION_RATE` | 手续费率 | `0.0003` |
| `SLIPPAGE` | 滑点比例 | `0.001` |
| `CORS_ORIGINS` | 允许的前端来源（逗号分隔） | `http://localhost:80,...` |
