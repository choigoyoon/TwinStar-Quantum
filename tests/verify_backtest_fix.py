import pandas as pd
from core.strategy_core import AlphaX7Core
import os

def test_backtest_return():
    print("Testing backtest return type...")
    strategy = AlphaX7Core(use_mtf=True)
    
    # Load dummy data or actual data
    data_path = r"data\cache\upbit_btc_15m.parquet"
    if not os.path.exists(data_path):
        print(f"Data not found at {data_path}")
        return
        
    df = pd.read_parquet(data_path).iloc[:500]
    
    # Mock pattern data (resampled)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df_1h = df.set_index('timestamp').resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    print("Calling run_backtest with collect_audit=True...")
    # This should return a tuple (trades, audit_logs)
    result = strategy.run_backtest(
        df_pattern=df_1h,
        df_entry=df,
        collect_audit=True,
        return_state=False
    )
    
    print(f"Result type: {type(result)}")
    if isinstance(result, tuple):
        print(f"Result length: {len(result)}")
        trades, audits = result
        print(f"Trades count: {len(trades)}")
        print(f"Audits count: {len(audits)}")
        print("✅ Success: Tuple returned")
    else:
        print("❌ Failure: Tuple not returned")
        print(f"Result: {result}")

if __name__ == "__main__":
    test_backtest_return()
