
import ccxt
import time
from datetime import datetime

def test_upbit_fetch():
    try:
        exchange = ccxt.upbit()
        symbol = 'BTC/KRW'
        timeframe = '1m'
        
        # 2024년 1월 1일
        since_str = "2024-01-01 00:00:00"
        since_ts = int(datetime.strptime(since_str, "%Y-%m-%d %H:%M:%S").timestamp() * 1000)
        
        print(f"Testing Upbit fetch for {symbol} since {since_str}")
        
        all_candles = []
        current_since = since_ts
        
        for i in range(5): # Try 5 pages
            print(f"Fetching page {i+1} since {datetime.fromtimestamp(current_since/1000)}")
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=200)
            
            if not ohlcv:
                print("No data returned.")
                break
                
            print(f"Fetched {len(ohlcv)} candles. First: {datetime.fromtimestamp(ohlcv[0][0]/1000)}")
            all_candles.extend(ohlcv)
            current_since = ohlcv[-1][0] + 60000
            time.sleep(0.2)
            
        print(f"Total collected: {len(all_candles)}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_upbit_fetch()
