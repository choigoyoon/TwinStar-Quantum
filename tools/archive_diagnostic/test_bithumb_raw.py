
import requests
import json
from datetime import datetime

def test_bithumb_raw_api():
    base_url = "https://api.bithumb.com/public/candlestick/BTC_KRW/1m"
    
    print(f"Requesting: {base_url}")
    try:
        resp = requests.get(base_url, headers={"User-Agent": "Mozilla/5.0"})
        data = resp.json()
        
        if data.get("status") == "0000":
            candles = data.get("data", [])
            print(f"Total raw candles returned: {len(candles)}")
            if candles:
                first_ts = candles[0][0]
                last_ts = candles[-1][0]
                print(f"First: {datetime.fromtimestamp(first_ts/1000)}")
                print(f"Last: {datetime.fromtimestamp(last_ts/1000)}")
        else:
            print("Error response:", data)
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_bithumb_raw_api()
