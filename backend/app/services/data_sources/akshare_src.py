# backend/app/services/data_sources/akshare_src.py
from .base import DataSource  # 确保基类名已改
from typing import Optional, Dict, Any
import pandas as pd  # <--- 必须添加这一行
import akshare as ak

class AkShareSource(DataSource):  # <--- 类名改为 AkShareSource
    @property
    def name(self) -> str:
        return "AkShare"

    def get_realtime(self, symbol: str) -> Optional[Dict[str, Any]]:
        print(f"🔍 [AkShare Debug] 尝试获取: {symbol}")
        clean_symbol = symbol.replace("sh", "").replace("sz", "")
        symbols_to_try = [f"sh{clean_symbol}", f"{clean_symbol}.SH", clean_symbol]
        
        for sym in symbols_to_try:
            try:
                import akshare as ak
                print(f"🔗 [AkShare Debug] 调用 ak.stock_bid_ask_em(symbol='{sym}')")
                df = ak.stock_bid_ask_em(symbol=sym)
                
                if df is None:
                    print(f"⚠️ [AkShare Debug] 返回 DataFrame 为 None")
                    continue
                if df.empty:
                    print(f"⚠️ [AkShare Debug] 返回 DataFrame 为空")
                    continue
                    
                print(f"✅ [AkShare Debug] 成功获取数据，列名: {df.columns.tolist()}")
                item = df.iloc[0]
                return {
                    "source": self.name,
                    "price": float(item.get('最新价', 0)),
                    "change_percent": float(item.get('涨跌幅', 0)),
                    "symbol": sym
                }
            except Exception as e:
                print(f"❌ [AkShare Debug] 调用 {sym} 失败: {e}")
                # 继续尝试下一个格式
                continue
        return None

    def get_history(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        try:
            clean_symbol = symbol.replace("sh", "").replace("sz", "")
            df = ak.stock_zh_a_hist(symbol=clean_symbol, period="daily", 
                                    start_date=start_date.replace("-",""), 
                                    end_date=end_date.replace("-",""),
                                    adjust="qfq")
            if not df.empty:
                return df.rename(columns={
                    '日期': 'date', '开盘': 'open', '收盘': 'close', 
                    '最高': 'high', '最低': 'low', '成交量': 'volume'
                })[['date', 'open', 'high', 'low', 'close', 'volume']]
        except Exception as e:
            print(f"[{self.name}] 历史数据获取失败: {e}")
        return None