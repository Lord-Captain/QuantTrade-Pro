# backend/app/services/data_sources/factory.py
from typing import List, Optional, Dict, Any
import importlib
import pandas as pd
from .base import DataSource
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 可选数据源注册表：按优先级排序，(模块名, 类名)
# 采用懒加载：某个数据源的第三方库未安装时跳过该源，不影响其他源与整体启动
_SOURCE_REGISTRY = [
    ("tushare_src", "TushareSource"),
    ("sina_src", "SinaSource"),
    ("akshare_src", "AkShareSource"),
]


def _load_sources() -> List[DataSource]:
    sources: List[DataSource] = []
    for module_name, class_name in _SOURCE_REGISTRY:
        try:
            module = importlib.import_module(f".{module_name}", package=__package__)
            sources.append(getattr(module, class_name)())
        except ImportError as e:
            logger.warning("数据源 %s 不可用（依赖未安装: %s），已跳过", class_name, e)
        except Exception as e:
            logger.warning("数据源 %s 初始化失败: %s，已跳过", class_name, e)
    return sources


class DataSourceFactory:
    def __init__(self):
        # 注册所有数据源 (按优先级排序)
        self.sources: List[DataSource] = _load_sources()
        if not self.sources:
            logger.error("没有可用的数据源！请检查依赖安装")
        
        # 状态控制
        self.auto_switch_enabled = True
        self.manual_selected_index = 0
        
        # 记录最后一次成功获取数据的数据源实例
        self.last_successful_source: Optional[DataSource] = self.sources[0] if self.sources else None

    def get_available_sources(self) -> List[Dict[str, Any]]:
        """获取所有可用数据源列表"""
        # 【修改】在自动模式下，"当前"指的是 last_successful_source
        current_name = self.get_current_source().name
        return [
            {"name": s.name, "is_current": s.name == current_name}
            for s in self.sources
        ]

    def get_current_source(self) -> DataSource:
        """获取当前正在使用的数据源 (用于前端显示)"""
        if self.auto_switch_enabled:
            return self.last_successful_source if self.last_successful_source else self.sources[0]
        return self.sources[self.manual_selected_index]

    def set_auto_mode(self, enable: bool):
        """切换自动/手动模式"""
        self.auto_switch_enabled = enable
        # 切回自动模式时，不需要重置 last_successful_source，保留最近的成功记录

    def set_manual_source(self, source_name: str):
        """手动指定数据源"""
        for i, source in enumerate(self.sources):
            if source.name == source_name:
                self.manual_selected_index = i
                self.auto_switch_enabled = False
                # 手动指定成功后，更新 last_successful_source
                self.last_successful_source = source
                return
        raise ValueError(f"未找到数据源：{source_name}")

    def get_realtime(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取实时数据"""
        if self.auto_switch_enabled:
            for i, source in enumerate(self.sources):
                try:
                    data = source.get_realtime(symbol)
                    if data:
                        if self.last_successful_source != source:
                            logger.info("数据源切换: %s -> %s",
                                        self.last_successful_source.name if self.last_successful_source else 'None',
                                        source.name)
                            self.last_successful_source = source
                        if i != 0:
                            logger.warning("主数据源失败，自动降级到 [%s]", source.name)
                        return data
                except Exception as e:
                    logger.warning("[%s] 获取实时数据异常: %s", source.name, e)
                    continue

            logger.error("所有数据源均失败 (symbol=%s)", symbol)
            # 即使全失败，也不清除 last_successful_source，保持显示上一次成功的，直到有新成功者
            return None
        else:
            # 手动模式
            source = self.sources[self.manual_selected_index]
            try:
                data = source.get_realtime(symbol)
                if data:
                    self.last_successful_source = source  # 手动成功也更新记录
                return data
            except Exception as e:
                logger.warning("[%s] 获取实时数据异常: %s", source.name, e)
                return None

    def get_history(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取历史数据，自动模式下按优先级依次尝试各数据源"""
        candidates = self.sources if self.auto_switch_enabled else [self.sources[self.manual_selected_index]]
        for source in candidates:
            if not hasattr(source, 'get_history'):
                continue
            try:
                df = source.get_history(symbol, start_date, end_date)
                if df is not None and not df.empty:
                    self.last_successful_source = source
                    return df
            except Exception as e:
                logger.warning("[%s] 获取历史数据异常: %s", source.name, e)
                continue
        return None
# 单例
factory = DataSourceFactory()