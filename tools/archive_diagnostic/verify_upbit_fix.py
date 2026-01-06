from GUI.data_manager import DataManager
import pandas as pd
from datetime import datetime, timedelta

def verify_upbit_fix():
    print("Verifying Upbit Pagination Fix...")
    dm = DataManager()
    
    # 3일전부터 데이터 요청 (1시간봉 기준 72개 이상, 1분봉 기준 4320개)
    # limit를 500으로 설정하여 200개를 넘는지 확인
    
    symbol = "BTC/KRW"
    timeframe = "5m"
    limit = 600
    
    print(f"Fetching {limit} candles for {symbol} ({timeframe})...")
    
    data = dm._fetch_ohlcv(symbol, timeframe, 'upbit', since=None, limit=limit)
    
    count = len(data)
    print(f"Fetched count: {count}")
    
    if count > 200:
        print("✅ SUCCESS: Fetched more than 200 candles.")
    elif count == 0:
        print("❌ FAIL: Fetched 0 candles.")
    else:
        print(f"⚠️ WARNING: Fetched {count} candles (Limit 200 might still be active or not enough data).")

if __name__ == "__main__":
    verify_upbit_fix()
