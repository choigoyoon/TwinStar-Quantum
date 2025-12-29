import ccxt
import pandas as pd
import time
from datetime import datetime

def test_upbit_pagination():
    print("Testing Upbit Pagination with CCXT...")
    upbit = ccxt.upbit()
    symbol = 'BTC/KRW'
    timeframe = '1h'
    
    # 24 hours ago
    since = upbit.parse8601(datetime.now().strftime('%Y-%m-%d 00:00:00')) - (48 * 60 * 60 * 1000) # 48 hours ago
    limit = 500 # Request more than 200
    
    print(f"Requesting {limit} candles since {datetime.fromtimestamp(since/1000)}")
    
    all_candles = []
    
    while len(all_candles) < limit:
        remaining = limit - len(all_candles)
        print(f"Fetching batch (since={since}, limit={remaining})...")
        candles = upbit.fetch_ohlcv(symbol, timeframe, since=since, limit=remaining)
        
        if not candles:
            print("No candles returned.")
            break
            
        print(f"Received {len(candles)} candles.")
        all_candles.extend(candles)
        
        last_ts = candles[-1][0]
        since = last_ts + 1
        
        if len(candles) < 200 and remaining > 200:
             print("Warning: Received less than 200, might be end of data or limit reached.")
        
        time.sleep(0.5)

    print(f"Total collected: {len(all_candles)}")
    if len(all_candles) == 200:
        print("FAIL: Stopped exactly at 200.")
    elif len(all_candles) > 200:
        print("SUCCESS: Pagination working.")
    else:
        print(f"Result: {len(all_candles)}")

if __name__ == "__main__":
    test_upbit_pagination()
