# backend/app/services/data_sources/base.py
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import pandas as pd

class DataSource(ABC):  # <--- 类名改为 DataSource
    """数据源抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def get_realtime(self, symbol: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_history(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        pass