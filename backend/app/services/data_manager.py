# backend/app/services/data_manager.py
import pandas as pd
import os
from datetime import datetime
from typing import Optional, Dict
from .data_sources.factory import factory as ds_factory

class DataManager:
    def __init__(self, data_dir: str = "./data/historical"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)

    def get_realtime_data(self, symbol: str) -> Optional[Dict]:
        """获取实时数据 (自动多源切换)"""
        # 【修复点】删除 auto_fallback 参数，工厂类内部会根据 self.auto_switch_enabled 自动判断
        return ds_factory.get_realtime(symbol)

    def get_historical_data(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        """获取历史数据 (优先本地缓存，其次多源拉取)"""
        # 1. 尝试本地缓存
        cache_file = f"{self.data_dir}/{symbol}_{start_date}_{end_date}.csv"
        if os.path.exists(cache_file):
            print(f"💾 命中本地缓存：{cache_file}")
            return pd.read_csv(cache_file, parse_dates=['date'])

        # 2. 本地没有，委托工厂拉取
        df = ds_factory.get_history(symbol, start_date, end_date)
        
        # 3. 如果拉取成功，存入缓存
        if df is not None and not df.empty:
            df.to_csv(cache_file, index=False)
            print(f"💾 已保存数据到本地缓存：{cache_file}")
            
        return df

    def switch_data_source(self, source_name: str):
        """供 API 调用，手动切换数据源"""
        ds_factory.set_manual_source(source_name)