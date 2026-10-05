# backend/tests/test_registry.py
"""策略注册中心测试"""
import pytest

from app.strategies.registry import registry
from app.strategies.base import StrategyBase


class TestStrategyRegistry:
    def test_builtin_strategies_registered(self):
        ids = {s["id"] for s in registry.get_all_strategies()}
        assert {"dual_ma", "momentum", "grid"} <= ids

    def test_metadata_complete_for_frontend(self):
        for s in registry.get_all_strategies():
            assert s["id"] and s["name"] and s["description"]
            assert isinstance(s["params"], list)
            for p in s["params"]:
                assert {"key", "label", "type", "default"} <= set(p)

    def test_get_all_strategies_excludes_class_ref(self):
        # 元数据必须可 JSON 序列化，不能泄漏类引用
        for s in registry.get_all_strategies():
            assert "class_ref" not in s

    def test_create_instance(self):
        instance = registry.create_instance("dual_ma", {"short_window": 3, "long_window": 10})
        assert isinstance(instance, StrategyBase)
        assert instance.short_window == 3
        assert instance.long_window == 10

    def test_create_instance_with_none_params(self):
        # 防御性：params 传 None 不应崩溃
        instance = registry.create_instance("momentum", None)
        assert isinstance(instance, StrategyBase)

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError, match="不存在"):
            registry.create_instance("not_exist")
        with pytest.raises(ValueError, match="不存在"):
            registry.get_strategy_info("not_exist")
