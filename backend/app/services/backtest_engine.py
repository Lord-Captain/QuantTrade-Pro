# backend/app/services/backtest_engine.py
import pandas as pd
from typing import Dict, List, Any
from app.strategies.base import StrategyBase
from app.services.data_manager import DataManager

class BacktestEngine:
    def __init__(self):
        self.dm = DataManager()

    def run_with_instance(self, symbol: str, start_date: str, end_date: str, strategy_instance: StrategyBase) -> Dict[str, Any]:
        """
        直接传入策略实例进行回测（推荐方式）
        """
        print(f"🚀 开始回测：{symbol} ({start_date} ~ {end_date}) | 策略：{strategy_instance.__class__.__name__}")
        
        # 1. 获取历史数据
        df = self.dm.get_historical_data(symbol, start_date, end_date)
        if df is None or df.empty:
            raise Exception("未获取到历史数据")
        
        print(f"📊 [回测] 获取到 {len(df)} 行数据。列名：{list(df.columns)}")
        print(f"📊 [回测] 首行数据预览：{df.iloc[0].to_dict()}")
        print(f"📊 [回测] 末行数据预览：{df.iloc[-1].to_dict()}")
        
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        
        # 2. 初始化记录
        first_close = float(df.iloc[0]['close'])
        min_cash_needed = first_close * 100 * 1.05 # 需要 105% 的钱 (留 5% 余量)
        
        if strategy_instance.cash < min_cash_needed:
            old_cash = strategy_instance.cash
            strategy_instance.cash = min_cash_needed
            print(f"⚠️ [资金调整] 初始资金 ({old_cash:.2f}) 不足以购买 1 手 {symbol} (需 {min_cash_needed:.2f})，已自动调整为 {strategy_instance.cash:.2f}")
        
        capital_curve = []
        trades = []
        initial_cash = strategy_instance.cash
        
        signal_count = 0 # 计数器

        # 3. 逐日回测
        for index, row in df.iterrows():
            date = row['date']
            open_p, high_p, low_p, close_p, volume = row['open'], row['high'], row['low'], row['close'], row['volume']
            
            try:
                signal = strategy_instance.on_bar(date, open_p, high_p, low_p, close_p, volume)
                # 【调试】每天打印一次信号，或者只在有信号时打印
                if index < 5 or signal: # 前5天和所有产生信号的天都打印
                    print(f"📅 [{date}] 收盘价:{close_p:.2f} | 信号：{signal} | 现金:{strategy_instance.cash:.2f} | 持仓:{strategy_instance.position}")
                
                if signal:
                    signal_count += 1

            except Exception as e:
                print(f"⚠️ 策略在 {date} 执行出错：{e}")
                signal = None
            
            # 交易逻辑 (简化版)
            if signal == 'buy':
                # 计算最大可买数量 (整手)
                max_buy_qty = int(strategy_instance.cash * 0.95 / close_p / 100) * 100
                
                if max_buy_qty >= 100:
                    cost = max_buy_qty * close_p
                    strategy_instance.cash -= cost
                    strategy_instance.position += max_buy_qty
                    trades.append({'date': date, 'type': 'buy', 'price': close_p, 'qty': max_buy_qty})
                    print(f"  💰 [{date}] 买入成功：{max_buy_qty}股 @ {close_p:.2f}, 花费 {cost:.2f}, 剩余现金 {strategy_instance.cash:.2f}")
                else:
                    # 【关键日志】告诉用户为什么没买
                    print(f"  ⚠️ [{date}] 买入失败：资金不足！当前现金 {strategy_instance.cash:.2f}, 股价 {close_p:.2f}, 最少需 {close_p*100:.2f}")
                    
                    
            elif signal == 'sell' and strategy_instance.position > 0:
                revenue = strategy_instance.position * close_p
                strategy_instance.cash += revenue
                trades.append({'date': date, 'type': 'sell', 'price': close_p, 'qty': strategy_instance.position})
                strategy_instance.position = 0
                
            current_asset = strategy_instance.get_current_asset(close_p)
            capital_curve.append({'date': date, 'asset': round(current_asset, 2)})
        print(f"🏁 [回测结束] 总天数:{len(df)}, 产生信号次数:{signal_count}, 最终交易笔数:{len(trades)}")
        if not capital_curve:
            raise Exception("回测结果为空：未生成任何资金曲线数据")
        
        if signal_count == 0:
            print("⚠️ 警告：策略在整个回测期间未产生任何买卖信号！请检查策略逻辑或数据时间跨度。")
            
            
            
        # 4. 计算指标
        if not capital_curve:
            raise Exception("回测结果为空")
            #4.1 提取最终资产
        final_asset = capital_curve[-1]['asset']
        total_return = (final_asset - initial_cash) / initial_cash * 100
        
        # 4.2 计算最大回撤 (增加防御性判断)
        assets = [x['asset'] for x in capital_curve]
        max_drawdown = 0.0
        peak = assets[0]
        for asset in assets:
            if asset > peak: peak = asset
            dd = (peak - asset) / peak * 100
            if dd > max_drawdown: max_drawdown = dd
        # 4.3. 【关键修复】清洗数据，确保所有字段都是 JSON 可序列化的原生类型
        # 清洗资金曲线
        clean_capital_curve = []
        for item in capital_curve:
            clean_capital_curve.append({
                "date": str(item['date']),          # 确保是字符串
                "asset": float(item['asset'])       # 确保是浮点数
            })
            
        # 清洗交易记录
        clean_trades = []
        for item in trades:
            clean_trades.append({
                "date": str(item['date']),          # 确保是字符串
                "type": str(item['type']),          # buy/sell
                "price": float(item['price']),      # 确保是浮点数
                "qty": int(item['qty'])             # 确保是整数
            })
        # 4. 构建返回字典
        result = {
            "symbol": symbol,
            "initial_cash": float(initial_cash),
            "final_asset": round(final_asset, 2),
            "total_return": round(float(total_return), 2),
            "max_drawdown": round(float(max_drawdown), 2),
            "trades": clean_trades,                 # 使用清洗后的列表
            "capital_curve": clean_capital_curve,   # 使用清洗后的列表
            "position_curve": [] # 如果需要也可以清洗，暂时留空或同样处理
        }
        print(f"✅ [回测成功] 收益率：{result['total_return']}%, 最大回撤：{result['max_drawdown']}%")
        return result

    # 保留旧方法以兼容，但内部可调用新方法
    def run(self, symbol: str, start_date: str, end_date: str, strategy_code: str, class_name: str, params: Dict = None) -> Dict[str, Any]:
        # 这里可以保留之前的 exec 逻辑作为备用，或者直接废弃
        raise NotImplementedError("请使用 run_with_instance 方法")