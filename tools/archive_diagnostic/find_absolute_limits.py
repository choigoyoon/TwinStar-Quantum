
import ccxt
import time
from datetime import datetime, timedelta

def find_max_limit(exchange_id, symbol='BTC/KRW', timeframe='1m'):
    print(f"\n===== Finding Max Limit for {exchange_id.upper()} =====")
    try:
        exchange = getattr(ccxt, exchange_id)()
        all_candles = []
        
        # Test 1: Forward from very old date
        # Some exchanges (like Upbit) allow fetching far back if since is provided
        since = int((datetime.now() - timedelta(days=365)).timestamp() * 1000)
        
        print(f"Attempting to fetch {exchange_id} starting from 1 year ago...")
        
        # We'll use the logic similar to our DataManager
        current_since = since
        max_batch = 1000 if exchange_id == 'upbit' else 200
        
        total_fetched = 0
        while True:
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=current_since, limit=max_batch)
                if not ohlcv:
                    break
                
                # Check for duplicates
                if all_candles and ohlcv[0][0] == all_candles[-1][0]:
                    break
                    
                all_candles.extend(ohlcv)
                total_fetched += len(ohlcv)
                
                # Update since
                current_since = ohlcv[-1][0] + 60000
                
                # Print progress
                first_date = datetime.fromtimestamp(ohlcv[0][0]/1000).strftime('%Y-%m-%d %H:%M')
                last_date = datetime.fromtimestamp(ohlcv[-1][0]/1000).strftime('%Y-%m-%d %H:%M')
                print(f"   Batch: {len(ohlcv)} candles [{first_date} ~ {last_date}]")
                
                if total_fetched > 20000: # Limit test range
                    print("   (Test capped at 20,000 for speed)")
                    break
                    
                time.sleep(0.1)
            except Exception as e:
                print(f"   Error: {e}")
                break
                
        print(f"===== {exchange_id.upper()} SUMMARY =====")
        if all_candles:
            start_d = datetime.fromtimestamp(all_candles[0][0]/1000).strftime('%Y-%m-%d')
            end_d = datetime.fromtimestamp(all_candles[-1][0]/1000).strftime('%Y-%m-%d')
            print(f"Total: {len(all_candles)} candles")
            print(f"Range: {start_d} to {end_d}")
        else:
            print("No data found.")
            
    except Exception as e:
        print(f"Outer Error: {e}")

if __name__ == "__main__":
    find_max_limit('upbit')
    find_max_limit('bithumb')
