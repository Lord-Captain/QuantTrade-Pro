# backend/app/services/data_sources/factory.py
from typing import List, Optional, Dict, Any
import pandas as pd
from .base import DataSource
from .akshare_src import AkShareSource
from .sina_src import SinaSource
from .tushare_src import TushareSource  # <--- 新增导入

class DataSourceFactory:
    def __init__(self):
        # 注册所有数据源 (按优先级排序)
        self.sources: List[DataSource] = [
            TushareSource(),
            SinaSource(),
            AkShareSource()
            
        ]
        
        # 状态控制
        self.auto_switch_enabled = True
        self.manual_selected_index = 0
        
        # 【新增】记录最后一次成功获取数据的数据源实例
        self.last_successful_source: Optional[DataSource] = self.sources[0]

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
            target = self.last_successful_source if self.last_successful_source else self.sources[0]
            # 【强制调试】每次被调用都打印出来
            print(f"👀 [DEBUG] get_current_source 被调用 -> 自动模式 -> 返回：{target.name} (last_successful={self.last_successful_source.name if self.last_successful_source else 'None'})")
            return target
        else:
            target = self.sources[self.manual_selected_index]
            print(f"👀 [DEBUG] get_current_source 被调用 -> 手动模式 -> 返回：{target.name}")
            return target

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
                print(f"🔄 [自动模式] 尝试数据源 [{source.name}]...")
                try:
                    data = source.get_realtime(symbol)
                    if data:
                        # 【关键】记录成功的数据源
                        if self.last_successful_source != source:
                            print(f"🔄 [状态更新] 检测到新成功源！将 last_successful_source 从 [{self.last_successful_source.name if self.last_successful_source else 'None'}] 更新为 [{source.name}]")
                            self.last_successful_source = source
                        else:
                            print(f"ℹ️ [状态保持] 成功源依然是 [{source.name}]")
                            
                        if i != 0 and self.sources[0] == self.last_successful_source:
                             pass # 已经是主源，不用提示降级
                        elif i != 0:
                            print(f"⚠️ 主数据源失败，自动降级到 [{source.name}]")
                        
                        # 【核弹级调试】返回前最后一次确认
                        print(f"🔒 [返回前确认] 即将返回数据。此时 last_successful_source = {self.last_successful_source.name}")
                        print(f"🔒 [返回前确认] get_current_source() 将返回 = {self.get_current_source().name}")

                        return data
                except Exception as e:
                    print(f"❌ [{source.name}] 发生异常：{e}")
                    continue
            
            print("💥 所有数据源均失败")
            # 即使全失败，也不清除 last_successful_source，保持显示上一次成功的，直到有新成功者
            return None
        else:
            # 手动模式
            source = self.sources[self.manual_selected_index]
            print(f"🔒 [手动模式] 仅使用数据源 [{source.name}]")
            try:
                data = source.get_realtime(symbol)
                if data:
                    self.last_successful_source = source # 手动成功也更新记录
                return data
            except Exception as e:
                print(f"❌ [{source.name}] 异常：{e}")
                return None

    # 在 factory.py 中添加
    def get_history(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        if self.auto_switch_enabled:
            for source in self.sources:
                # 优先找有 get_history 能力的源 (Tushare)
                if hasattr(source, 'get_history'):
                    try:
                        df = source.get_history(symbol, start_date, end_date)
                        if df is not None and not df.empty:
                            self.last_successful_source = source
                            return df
                    except:
                        continue
        else:
            source = self.sources[self.manual_selected_index]
            if hasattr(source, 'get_history'):
                try:
                    df = source.get_history(symbol, start_date, end_date)
                    if df is not None and not df.empty:
                        self.last_successful_source = source
                        return df
                except:
                    pass
        return None
# 单例
factory = DataSourceFactory()