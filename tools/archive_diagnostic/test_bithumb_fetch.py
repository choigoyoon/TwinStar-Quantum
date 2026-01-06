
import ccxt
from datetime import datetime

def test_bithumb_fetch():
    try:
        exchange = ccxt.bithumb()
        symbol = 'BTC/KRW'
        timeframe = '1m'
        
        print(f"Testing Bithumb fetch for {symbol} with since=None")
        
        # Fetch without since
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=None) # limit=None to get max
        print(f"Fetched {len(ohlcv)} candles.")
        if ohlcv:
            print(f"First: {datetime.fromtimestamp(ohlcv[0][0]/1000)}")
            print(f"Last: {datetime.fromtimestamp(ohlcv[-1][0]/1000)}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_bithumb_fetch()
