# backend/app/services/backtest_engine.py
"""事件驱动回测引擎：逐 bar 撮合，计入手续费与滑点，输出完整绩效指标"""
import math
from typing import Any, Dict, List, Optional

import pandas as pd

from app.config import settings
from app.services.data_manager import DataManager
from app.strategies.base import StrategyBase
from app.utils.logger import get_logger

logger = get_logger(__name__)

TRADING_DAYS_PER_YEAR = 252


class BacktestEngine:
    def __init__(
        self,
        commission_rate: Optional[float] = None,
        slippage: Optional[float] = None,
    ):
        self.dm = DataManager()
        # 默认读取全局配置，允许单次回测覆盖
        self.commission_rate = commission_rate if commission_rate is not None else settings.COMMISSION_RATE
        self.slippage = slippage if slippage is not None else settings.SLIPPAGE

    def run_with_instance(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        strategy_instance: StrategyBase,
    ) -> Dict[str, Any]:
        """直接传入策略实例进行回测"""
        logger.info(
            "开始回测: %s (%s ~ %s) | 策略: %s",
            symbol, start_date, end_date, strategy_instance.__class__.__name__,
        )

        # 1. 获取历史数据
        df = self.dm.get_historical_data(symbol, start_date, end_date)
        if df is None or df.empty:
            raise ValueError(f"未获取到 {symbol} 在 {start_date}~{end_date} 的历史数据")

        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        logger.info("获取到 %d 行行情数据", len(df))

        # 2. 初始资金防御性调整：至少能买 1 手
        first_close = float(df.iloc[0]["close"])
        min_cash_needed = first_close * 100 * 1.05
        if strategy_instance.cash < min_cash_needed:
            logger.warning(
                "初始资金 %.2f 不足以购买 1 手 %s，自动调整为 %.2f",
                strategy_instance.cash, symbol, min_cash_needed,
            )
            strategy_instance.cash = min_cash_needed

        initial_cash = strategy_instance.cash
        capital_curve: List[Dict] = []
        trades: List[Dict] = []

        # 基准曲线：一开始按整手满仓买入并持有
        benchmark_shares = int(initial_cash / first_close / 100) * 100
        benchmark_cash = initial_cash - benchmark_shares * first_close
        benchmark_curve: List[Dict] = []

        # 胜率统计所需的持仓成本
        position_cost = 0.0
        closed_pnls: List[float] = []

        # 3. 逐日回测（当日信号按当日收盘价撮合，含滑点与手续费）
        for _, row in df.iterrows():
            date = row["date"]
            close_p = float(row["close"])

            try:
                signal = strategy_instance.on_bar(
                    date, row["open"], row["high"], row["low"], row["close"], row["volume"]
                )
            except Exception as e:
                logger.warning("策略在 %s 执行出错: %s", date, e)
                signal = None

            if signal == "buy":
                buy_price = close_p * (1 + self.slippage)
                # 预留手续费后的最大可买数量（整手）
                max_buy_qty = int(
                    strategy_instance.cash / (buy_price * (1 + self.commission_rate)) / 100
                ) * 100
                if max_buy_qty >= 100:
                    cost = max_buy_qty * buy_price
                    commission = cost * self.commission_rate
                    strategy_instance.cash -= cost + commission
                    strategy_instance.position += max_buy_qty
                    position_cost += cost + commission
                    trades.append({
                        "date": date, "type": "buy", "price": round(buy_price, 4),
                        "qty": max_buy_qty, "commission": round(commission, 2),
                    })
                    logger.debug("%s 买入 %d 股 @ %.2f", date, max_buy_qty, buy_price)
                else:
                    logger.debug("%s 资金不足，买入信号跳过", date)

            elif signal == "sell" and strategy_instance.position > 0:
                sell_price = close_p * (1 - self.slippage)
                qty = strategy_instance.position
                revenue = qty * sell_price
                commission = revenue * self.commission_rate
                strategy_instance.cash += revenue - commission
                closed_pnls.append(revenue - commission - position_cost)
                position_cost = 0.0
                strategy_instance.position = 0
                trades.append({
                    "date": date, "type": "sell", "price": round(sell_price, 4),
                    "qty": qty, "commission": round(commission, 2),
                })
                logger.debug("%s 卖出 %d 股 @ %.2f", date, qty, sell_price)

            capital_curve.append({
                "date": date,
                "asset": round(strategy_instance.get_current_asset(close_p), 2),
            })
            benchmark_curve.append({
                "date": date,
                "asset": round(benchmark_cash + benchmark_shares * close_p, 2),
            })

        if not capital_curve:
            raise ValueError("回测结果为空：未生成任何资金曲线数据")

        logger.info("回测结束: 共 %d 个交易日, 成交 %d 笔", len(capital_curve), len(trades))

        # 4. 计算绩效指标
        metrics = self._calc_metrics(capital_curve, benchmark_curve, initial_cash, closed_pnls)

        result = {
            "symbol": symbol,
            "initial_cash": float(initial_cash),
            "final_asset": capital_curve[-1]["asset"],
            "trades": trades,
            "capital_curve": capital_curve,
            "benchmark_curve": benchmark_curve,
            "position_curve": [],
            **metrics,
        }
        logger.info(
            "回测完成: 收益率 %.2f%%, 最大回撤 %.2f%%, 夏普比率 %.2f, 胜率 %.1f%%",
            metrics["total_return"], metrics["max_drawdown"],
            metrics["sharpe_ratio"], metrics["win_rate"],
        )
        return result

    def _calc_metrics(
        self,
        capital_curve: List[Dict],
        benchmark_curve: List[Dict],
        initial_cash: float,
        closed_pnls: List[float],
    ) -> Dict[str, float]:
        """计算收益率、最大回撤、年化收益、夏普比率、胜率等指标"""
        assets = [x["asset"] for x in capital_curve]
        final_asset = assets[-1]
        total_return = (final_asset - initial_cash) / initial_cash * 100

        benchmark_final = benchmark_curve[-1]["asset"]
        benchmark_return = (benchmark_final - initial_cash) / initial_cash * 100

        # 最大回撤
        max_drawdown = 0.0
        peak = assets[0]
        for asset in assets:
            peak = max(peak, asset)
            max_drawdown = max(max_drawdown, (peak - asset) / peak * 100)

        # 年化收益率（复利口径）
        days = len(assets)
        annualized_return = (
            ((final_asset / initial_cash) ** (TRADING_DAYS_PER_YEAR / days) - 1) * 100
            if days > 1 and final_asset > 0 else 0.0
        )

        # 夏普比率（基于日收益率，无风险利率取 0，年化 √252）
        daily_returns = [
            assets[i] / assets[i - 1] - 1 for i in range(1, len(assets)) if assets[i - 1] > 0
        ]
        sharpe_ratio = 0.0
        if len(daily_returns) > 1:
            mean_r = sum(daily_returns) / len(daily_returns)
            var = sum((r - mean_r) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
            std_r = math.sqrt(var)
            if std_r > 0:
                sharpe_ratio = mean_r / std_r * math.sqrt(TRADING_DAYS_PER_YEAR)

        # 胜率：已平仓的完整买卖回合中盈利占比
        round_trips = len(closed_pnls)
        win_rate = (
            sum(1 for p in closed_pnls if p > 0) / round_trips * 100 if round_trips else 0.0
        )

        return {
            "total_return": round(total_return, 2),
            "benchmark_return": round(benchmark_return, 2),
            "benchmark_final_asset": round(benchmark_final, 2),
            "max_drawdown": round(max_drawdown, 2),
            "annualized_return": round(annualized_return, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "win_rate": round(win_rate, 2),
            "round_trips": round_trips,
        }
