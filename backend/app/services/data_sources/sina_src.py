# backend/app/services/data_sources/sina_src.py
from .base import DataSource  # 确保基类名已改
from typing import Optional, Dict, Any
import requests
import pandas as pd  # <--- 必须添加这一行

class SinaSource(DataSource):  # <--- 类名改为 SinaSource
    @property
    def name(self) -> str:
        return "SinaFinance"

    def get_realtime(self, symbol: str) -> Optional[Dict[str, Any]]:
        print(f"🔍 [Sina Debug] 开始请求，原始代码：{symbol}")
        
        # 1. 代码格式化
        if not symbol.startswith("sh") and not symbol.startswith("sz"):
            prefix = "sh" if symbol.startswith('6') else "sz"
            symbol = f"{prefix}{symbol}"
            
        url = f"http://hq.sinajs.cn/list={symbol}"
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://finance.sina.com.cn/",
            }
            resp = requests.get(url, headers=headers, timeout=5)
            resp.encoding = 'gbk'
            
            if resp.status_code != 200:
                return None

            text = resp.text
            # print(f"Raw Text: {text}") # 调试用
            
            # 【关键修复】更健壮的提取逻辑
            if "=" not in text:
                return None
            
            # 1. 截取等号后面的部分
            raw_data = text.split('=')[1]
            
            # 2. 去除首尾的空白、引号、分号
            # 先 strip 空白，再 strip 引号，最后 strip 分号
            clean_data = raw_data.strip().strip('"').strip("'").rstrip(';').strip('"')
            
            # 3. 按逗号分割
            parts = clean_data.split(',')
            
            # 【关键调试】打印所有字段及其索引，找出成交量和成交额的真实位置
            print(f"🔍 [Sina Debug] 原始数据长度: {len(parts)}")
            print(f"🔍 [Sina Debug] 字段详情:")
            for i, val in enumerate(parts):
                # 只打印非空或关键的字段，避免日志太长
                if val.strip(): 
                    print(f"   [{i}]: '{val}'")
            
            # ... (前面的清洗和分割逻辑不变) ...
            
            # 【关键修复】智能识别成交量和成交额索引
            # 标准 Sina 接口结构：
            # 0:名称，1:今开，2:昨收，3:当前价，4:最高，5:最低
            # 6:竞价价(通常无用), 7:竞价量(通常无用)
            # 8:成交量 (手), 9:成交额 (元)  <-- 最稳定的位置！
            # 10-29: 买卖五档数据 (买1量，买1价，卖1价，卖1量...)
            # 30:日期，31:时间
            
            # 防御性检查：确保数组长度足够
            if len(parts) < 10:
                print(f"❌ [Sina] 数据严重缺失，长度仅 {len(parts)}")
                return None

            try:
                name = parts[0]
                
                def safe_float(val, default=0.0):
                    if not val or val == '':
                        return default
                    try:
                        return float(val)
                    except ValueError:
                        return default

                open_price = safe_float(parts[1])
                prev_close = safe_float(parts[2])
                current_price = safe_float(parts[3])
                high_price = safe_float(parts[4])
                low_price = safe_float(parts[5])
                
                # 【关键修复】Sina 返回的是“股”，需要除以 100 转换为“手”
                volume_shares = safe_float(parts[8])      # 原始数据 (股)
                volume_hand = volume_shares / 100.0       # 转换为 (手)
                
                amount_money = safe_float(parts[9])       # 成交额单位是元，无需转换
                
                # 日期和时间 (可能在最后，也可能因数据展开而移位)
                # 策略：从后往前找，找到第一个符合日期格式的字符串
                trade_date = ""
                trade_time = ""
                
                # 尝试标准位置 30, 31
                if len(parts) > 31:
                    if parts[30] and len(parts[30]) == 10 and '-' in parts[30]:
                        trade_date = parts[30]
                    if len(parts) > 31 and ':' in parts[31]:
                        trade_time = parts[31]
                
                # 如果标准位置没找到，尝试从后往前扫描
                if not trade_date:
                    for i in range(len(parts)-1, -1, -1):
                        p = parts[i]
                        if len(p) == 10 and '-' in p: # 简单判断日期
                            trade_date = p
                            if i+1 < len(parts) and ':' in parts[i+1]:
                                trade_time = parts[i+1]
                            break
                
                full_time = f"{trade_date} {trade_time}" if trade_date and trade_time else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                change_percent = ((current_price - prev_close) / prev_close * 100) if prev_close else 0.0
                change_amount = current_price - prev_close

                result = {
                    "source": self.name,
                    "symbol": symbol,
                    "name": name,
                    "price": current_price,
                    "change_percent": change_percent,
                    "change_amount": change_amount,
                    "open": open_price,
                    "prev_close": prev_close,
                    "high": high_price,
                    "low": low_price,
                    "volume": volume_hand,    # 现在应该是有值的了
                    "amount": amount_money,   # 现在应该是有值的了
                    "time": full_time
                }
                
                print(f"✅ [Sina] 解析成功：{name} ({current_price}), 量:{volume_hand}手, 额:{amount_money}元")
                return result

            except Exception as e:
                print(f"❌ [Sina] 映射过程出错: {e}")
                import traceback
                traceback.print_exc()
                return None

        except Exception as e:
            print(f"❌ [Sina] 请求异常: {e}")
            return None

    def get_history(self, symbol: str, start_date: str, end_date: str) -> Optional[pd.DataFrame]:
        # Sina 不适合大量历史数据，返回 None
        return None