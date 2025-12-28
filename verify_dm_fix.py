
import sys
import os
from datetime import datetime
import pandas as pd

# Add paths
sys.path.append(os.getcwd())
from GUI.data_manager import DataManager

def verify_data_manager():
    dm = DataManager()
    
    # Test Bithumb (should use batch 200)
    print("\n[Test 1] Testing Bithumb pagination with DataManager")
    df_bithumb = dm._fetch_ohlcv('BTC/KRW', '1m', 'bithumb', limit=500)
    print(f"Collected {len(df_bithumb)} candles from Bithumb.")
    
    # Test Upbit (should use batch 1000)
    print("\n[Test 2] Testing Upbit pagination with DataManager")
    df_upbit = dm._fetch_ohlcv('BTC/KRW', '1m', 'upbit', limit=1200)
    print(f"Collected {len(df_upbit)} candles from Upbit.")

if __name__ == "__main__":
    verify_data_manager()
