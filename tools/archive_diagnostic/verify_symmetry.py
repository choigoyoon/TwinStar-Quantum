import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.strategy_core import AlphaX7Core
from GUI.constants import get_params

import os

def run_verification():
    print("🚀 Starting Logic Symmetry Verification...")
    
    # 1. Load Data
    data_path = r"C:\매매전략\data\cache\bybit_btcusdt_15m.parquet"
    if not os.path.exists(data_path):
        print(f"❌ Data not found at {data_path}")
        return
    
    df_15m = pd.read_parquet(data_path)
    if pd.api.types.is_numeric_dtype(df_15m['timestamp']):
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
    
    # ACTIVE_PARAMS = get_params()
    # It seems strategy_core already uses ACTIVE_PARAMS internally if not passed.
    
    # Standardize 1H data from 15m (Correct alignment)

    df_1h = df_15m.set_index('timestamp').resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    # 2. Run Standard Backtest
    print("📊 Running Standard Backtest...")
    core = AlphaX7Core(use_mtf=True)
    trades_bt = core.run_backtest(df_1h, df_15m, slippage=0.0006)
    
    print(f"✅ Backtest completed: {len(trades_bt)} trades")
    
    # 3. Simulate UnifiedBot (FIXED logic)
    print("🤖 Simulating UnifiedBot FIXED Loop (if ts.minute==45 trigger)...")
    
    fixed_1h = []
    for i in range(len(df_15m)):
        ts = df_15m.iloc[i]['timestamp']
        if ts.minute == 45 and i >= 3:
            # Trigger 1H construction like FIXED unified_bot.py
            last_4 = df_15m.iloc[i-3:i+1] # 09:00, 09:15, 09:30, 09:45
            new_1h = {
                'timestamp': last_4.iloc[0]['timestamp'], # 09:00 (CORRECT)
                'open': last_4.iloc[0]['open'],
                'high': last_4['high'].max(),
                'low': last_4['low'].min(),
                'close': last_4.iloc[-1]['close'],
                'volume': last_4['volume'].sum()
            }
            fixed_1h.append(new_1h)
            
    df_fixed_1h = pd.DataFrame(fixed_1h)
    print(f"✅ Fixed 1H data created: {len(df_fixed_1h)} candles (starts with {df_fixed_1h.iloc[0]['timestamp']})")
    
    # 4. Run Backtest on Fixed Data
    print("📊 Running Backtest on Fixed Data...")
    trades_fixed = core.run_backtest(df_fixed_1h, df_15m, slippage=0.0006)
    print(f"✅ Fixed trades: {len(trades_fixed)} trades")
    
    # Comparison
    print(f"\n[Result Summary]")
    print(f"Standard Base (08:00): {len(trades_bt)} trades")
    print(f"Fixed Base    (09:00): {len(trades_fixed)} trades")
    print(f"Discrepancy: {abs(len(trades_bt) - len(trades_fixed))} trades ({abs(len(trades_bt)-len(trades_fixed))/len(trades_bt)*100:.2f}%)")



if __name__ == "__main__":
    # Ensure current directory is project root for imports
    import sys
    sys.path.append(os.getcwd())
    run_verification()
