# backend/app/services/data_sources/tushare_src.py
from .base import DataSource
from typing import Optional, Dict, Any
import pandas as pd
import tushare as ts
import requests
import os
from datetime import datetime


class TushareSource(DataSource):
    def __init__(self):
        # ✅ 在实例化时再获取 Token 和初始化 pro
        self.ts_token = os.getenv("TUSHARE_TOKEN")
        
        # 如果这里还是 None，说明 .env 没读到了（可能是 main.py 的 load_dotenv 也没生效，或者路径不对）
        # 为了调试，我们可以先打印一下，或者尝试硬编码 fallback
        if not self.ts_token:
            print("⚠️ 警告：环境变量 TUSHARE_TOKEN 为空！请检查 .env 文件或系统环境变量。")
            # 临时调试用：如果环境变量没有，可以尝试在这里硬编码（生产环境千万别这么做）
            # self.ts_token = "你的_TOKEN_硬编码在这里" 
            
            # 如果没有 Token，后续调用会失败，但我们先不抛异常，让程序能启动
            self.pro = None
        else:
            ts.set_token(self.ts_token)
            self.pro = ts.pro_api()
            print(f"✅ [Tushare] 初始化成功 (Token 前4位: {self.ts_token[:4]}...)")

    def _get_pro_api(self):
        """获取 pro 接口实例，如果未初始化则尝试初始化"""
        if self.pro is None:
            # 双重检查：也许环境变量在运行时被设置了？
            token = os.getenv("TUSHARE_TOKEN")
            if token:
                ts.set_token(token)
                self.pro = ts.pro_api()
            else:
                raise RuntimeError("Tushare Token 仍未配置，无法调用接口。请检查 .env 文件。")
        return self.pro
    
    @property
    def name(self) -> str:
        return "TusharePro"

    def _convert_symbol(self, symbol: str) -> str:
        """转换为 Tushare 格式 (600519.SH)"""
        clean = symbol.replace("sh", "").replace("sz", "")
        if symbol.startswith("sh"):
            return f"{clean}.SH"
        elif symbol.startswith("sz"):
            return f"{clean}.SZ"
        else:
            return f"{clean}.SH" if clean.startswith('6') else f"{clean}.SZ"

    def _get_name_from_sina(self, symbol: str) -> str:
        """从 Sina 获取股票名称"""
        print(f"🔍 [Sina 辅助] 开始尝试获取 [{symbol}] 的名称...")
        try:
            # 1. 格式化符号 (确保是 sh600519 格式)
            sina_symbol = symbol
            if not symbol.startswith(('sh', 'sz')):
                # 如果传入的是纯数字，自动补全
                prefix = "sh" if symbol.startswith('6') else "sz"
                sina_symbol = f"{prefix}{symbol}"
            
            url = f"http://hq.sinajs.cn/list={sina_symbol}"
            
            # 2. 【关键修复】添加完整的 Headers 伪装
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://finance.sina.com.cn/",  # 必须项！告诉 Sina 我们是从财经页来的
                "Accept": "*/*",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache"
            }
            
            print(f"🔗 [Sina 辅助] 请求 URL: {url}")
            
            # 3. 发送请求
            resp = requests.get(url, headers=headers, timeout=3) # 稍微增加超时时间
            
            print(f"📡 [Sina 辅助] 响应状态码：{resp.status_code}")
            
            if resp.status_code == 200 and '=' in resp.text:
                # 设置编码为 GBK (Sina 默认编码)
                resp.encoding = 'gbk' 
                
                data_part = resp.text.split('=')[1].strip().strip('"').rstrip(';')
                parts = data_part.split(',')
                if len(parts) > 0:
                    name = parts[0]
                    print(f"✅ [Sina 辅助] 成功获取名称：{name}")
                    return name
                else:
                    print(f"⚠️ [Sina 辅助] 解析失败，parts 为空")
            else:
                print(f"⚠️ [Sina 辅助] 请求失败，内容预览：{resp.text[:50]}")
                
        except Exception as e:
            print(f"❌ [Sina 辅助] 发生异常：{type(e).__name__} - {e}")
        
        return "未知股票"

    def get_realtime(self, symbol: str) -> Optional[Dict[str, Any]]:
        try:
            ts_code = self._convert_symbol(symbol)
            today = datetime.now().strftime("%Y%m%d")
            
            # 1. 【核心数据】从 Tushare 获取价格、涨跌幅等
            df = pro.daily(ts_code=ts_code, start_date=today, end_date=today)
            
            # 如果今天无数据，尝试昨天（防止盘后数据未更新）
            if df is None or df.empty:
                yesterday = (datetime.now() - pd.Timedelta(days=1)).strftime("%Y%m%d")
                df = pro.daily(ts_code=ts_code, start_date=yesterday, end_date=yesterday)
            
            # 再不行试前天（周末/节假日）
            if df is None or df.empty:
                last_trade = (datetime.now() - pd.Timedelta(days=2)).strftime("%Y%m%d")
                df = pro.daily(ts_code=ts_code, start_date=last_trade, end_date=last_trade)

            if df is None or df.empty:
                print(f"[Tushare] 未获取到 {ts_code} 的近期行情数据")
                return None

            row = df.iloc[0]
            close_price = float(row['close'])
            pre_close = float(row['pre_close'])
            print(f"🔄 [Tushare] 准备补充名称，当前 Tushare 返回无名称，调用 Sina 辅助...") # <--- 强制打印 6
            # 2. 【名称补充】Tushare daily 接口没名字，尝试从 Sina "借" 一个
            # 优先检查是否有缓存逻辑（可选），这里直接按需请求
            stock_name = self._get_name_from_sina(symbol) 
            # 如果 Sina 也挂了，至少我们还有价格数据，名字显示"未知"即可
            print(f"🏷️ [最终结果] 股票名称确定为：{stock_name}") # <--- 强制打印 7
            
            # 3. 数据组装
            volume_hand = float(row['vol'])       # Tushare vol 单位是手
            amount_yuan = float(row['amount']) * 1000 # Tushare amount 单位是千元 -> 元
            
            change_pct = ((close_price - pre_close) / pre_close * 100) if pre_close else 0
            
            return {
                "source": self.name,
                "symbol": ts_code,
                "name": stock_name,          # <--- 这里现在是 Sina 提供的名字了！
                "price": close_price,
                "change_percent": change_pct,
                "change_amount": close_price - pre_close,
                "open": float(row['open']),
                "prev_close": pre_close,
                "high": float(row['high']),
                "low": float(row['low']),
                "volume": volume_hand,
                "amount": amount_yuan,
                "time": str(row['trade_date'])
            }
        except Exception as e:
            print(f"[Tushare] 实时数据获取失败：{e}")
            import traceback
            traceback.print_exc()
            return None

    def get_history(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        # 历史数据不需要名字，直接用 Tushare 即可
        try:
            ts_code = self._convert_symbol(symbol)
            start_fmt = start_date.replace("-", "")
            end_fmt = end_date.replace("-", "")
            
            df = pro.daily(ts_code=ts_code, start_date=start_fmt, end_date=end_fmt)
            
            if df is None or df.empty:
                return None
            
            df.rename(columns={
                "trade_date": "date", "open": "open", "close": "close", 
                "high": "high", "low": "low", "vol": "volume", "amount": "amount"
            }, inplace=True)
            
            df['amount'] = df['amount'] * 1000
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            df.sort_values('date', inplace=True)
            
            return df
        except Exception as e:
            print(f"[Tushare] 历史数据获取失败：{e}")
            return None