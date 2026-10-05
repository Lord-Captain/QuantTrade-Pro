# backend/tests/test_strategies.py
"""策略信号单元测试：用合成价格序列验证各策略的买卖信号"""
import pytest

from app.strategies.dual_ma import DualMaStrategy
from app.strategies.momentum import MomentumStrategy
from app.strategies.grid_trading import GridTradingStrategy


def feed(strategy, closes):
    """依次喂入收盘价，返回每日信号列表"""
    signals = []
    for i, close in enumerate(closes):
        signals.append(strategy.on_bar(f"2025-01-{i+1:02d}", close, close, close, close, 1000))
    return signals


class TestDualMaStrategy:
    def test_no_signal_before_warmup(self):
        s = DualMaStrategy({"short_window": 2, "long_window": 5})
        signals = feed(s, [10.0] * 5)
        assert all(sig is None for sig in signals)

    def test_golden_cross_triggers_buy(self):
        # 先阴跌形成死叉状态，再突然拉升造成金叉
        s = DualMaStrategy({"short_window": 2, "long_window": 4})
        closes = [10.0, 9.5, 9.0, 8.5, 8.0, 8.0, 12.0]
        signals = feed(s, closes)
        assert "buy" in signals

    def test_death_cross_triggers_sell(self):
        # 先上涨形成多头排列，再暴跌造成死叉
        s = DualMaStrategy({"short_window": 2, "long_window": 4})
        closes = [8.0, 8.5, 9.0, 9.5, 10.0, 10.0, 7.0]
        signals = feed(s, closes)
        assert "sell" in signals

    def test_flat_prices_no_signal(self):
        s = DualMaStrategy({"short_window": 2, "long_window": 4})
        signals = feed(s, [10.0] * 20)
        assert all(sig is None for sig in signals)


class TestMomentumStrategy:
    def test_breakout_triggers_buy(self):
        s = MomentumStrategy({"lookback": 5, "stop_loss": 5.0})
        closes = [10.0] * 6 + [11.0]  # 第7天突破前5日高点
        signals = feed(s, closes)
        assert signals[-1] == "buy"

    def test_no_breakout_no_buy(self):
        s = MomentumStrategy({"lookback": 5, "stop_loss": 5.0})
        closes = [10.0] * 6 + [9.5]  # 未突破
        signals = feed(s, closes)
        assert all(sig is None for sig in signals)

    def test_stop_loss_triggers_sell(self):
        s = MomentumStrategy({"lookback": 5, "stop_loss": 5.0})
        # 先突破买入（模拟持仓），再跌破止损线
        closes = [10.0] * 6 + [11.0]
        feed(s, closes)
        s.position = 100  # 模拟引擎已建仓
        s.entry_price = 11.0
        signals = feed(s, [10.0])  # 跌幅 > 5% 触发止损
        assert signals[-1] == "sell"


class TestGridTradingStrategy:
    def test_first_day_only_sets_base_price(self):
        s = GridTradingStrategy({"grid_size": 2.0, "max_grid": 10})
        assert s.on_bar("2025-01-01", 100, 100, 100, 100, 1000) is None
        assert s.base_price == 100

    def test_price_drop_triggers_buy(self):
        s = GridTradingStrategy({"grid_size": 2.0, "max_grid": 10})
        feed(s, [100.0])
        signals = feed(s, [97.0])  # 下跌超过一格 (2%)
        assert signals[-1] == "buy"

    def test_price_rise_with_position_triggers_sell(self):
        s = GridTradingStrategy({"grid_size": 2.0, "max_grid": 10})
        feed(s, [100.0, 97.0])  # 先下跌买入
        s.position = 100
        signals = feed(s, [100.0])  # 涨回一格
        assert signals[-1] == "sell"

    def test_price_rise_without_position_no_sell(self):
        s = GridTradingStrategy({"grid_size": 2.0, "max_grid": 10})
        feed(s, [100.0])
        signals = feed(s, [103.0])  # 上涨但无持仓
        assert signals[-1] is None
