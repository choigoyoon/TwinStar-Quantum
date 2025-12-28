
import ccxt
from datetime import datetime

def test_limits():
    exchanges = ['upbit', 'bithumb']
    symbol = 'BTC/KRW'
    timeframe = '1m'
    limits_to_test = [200, 500, 1000, 3000, 5000]

    for ex_id in exchanges:
        print(f"\n--- Testing {ex_id.upper()} ---")
        try:
            exchange = getattr(ccxt, ex_id)()
            for limit in limits_to_test:
                print(f"Requesting limit={limit}...")
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
                print(f"Received {len(ohlcv)} candles.")
                if len(ohlcv) < limit:
                    print(f"Result: {ex_id} seems to hard limit at {len(ohlcv)}.")
                    break
                else:
                    print(f"Result: {ex_id} supports {limit} candles.")
        except Exception as e:
            print(f"Error testing {ex_id}: {e}")

if __name__ == "__main__":
    test_limits()
