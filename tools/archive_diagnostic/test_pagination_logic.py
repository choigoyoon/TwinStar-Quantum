
import ccxt
import time
from datetime import datetime

def test_pagination(exchange_id, symbol, target_count):
    print(f"\n===== Stress Testing {exchange_id.upper()} Pagination =====")
    try:
        exchange = getattr(ccxt, exchange_id)()
        all_candles = []
        
        # We start with since=None to get most recent, or a specific date
        # To test pagination, we go backwards or forwards. 
        # CCXT Upbit/Bithumb usually go backwards if since is not provided, 
        # but fetch_ohlcv with since goes forwards.
        
        # Let's try to get 1000 candles in batches of 200
        batch_size = 200
        since = None # Start from recent
        
        # To go backwards (historical), some exchanges require 'since' or specific logic.
        # But our app mostly goes FORWARDS from a start date or LAST_TS.
        
        # Test FORWARD pagination from 24 hours ago
        start_ts = int((time.time() - 24 * 3600) * 1000)
        current_since = start_ts
        
        print(f"Starting forward fetch for {target_count} candles from {datetime.fromtimestamp(start_ts/1000)}")
        
        fetched = 0
        while fetched < target_count:
            print(f"[{exchange_id}] Requesting {batch_size} candles since {datetime.fromtimestamp(current_since/1000)}")
            ohlcv = exchange.fetch_ohlcv(symbol, '1m', since=current_since, limit=batch_size)
            
            if not ohlcv:
                print(f"[{exchange_id}] No more data returned.")
                break
                
            print(f"[{exchange_id}] Received {len(ohlcv)} candles. (First: {datetime.fromtimestamp(ohlcv[0][0]/1000)}, Last: {datetime.fromtimestamp(ohlcv[-1][0]/1000)})")
            
            all_candles.extend(ohlcv)
            fetched += len(ohlcv)
            
            # Check if we are stuck
            if len(ohlcv) > 0:
                new_since = ohlcv[-1][0] + 60000
                if new_since == current_since:
                    print(f"[{exchange_id}] STUCK: same timestamp returned.")
                    break
                current_since = new_since
            else:
                break
                
            time.sleep(0.5) # Avoid rate limit
            
        print(f"[{exchange_id}] Final result: {len(all_candles)} candles collected.")
        return len(all_candles)
        
    except Exception as e:
        print(f"[{exchange_id}] Error: {e}")
        return 0

if __name__ == "__main__":
    # Test Upbit and Bithumb
    test_pagination('upbit', 'BTC/KRW', 1000)
    test_pagination('bithumb', 'BTC/KRW', 3000)
