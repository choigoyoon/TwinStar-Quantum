import sys
import os
import pandas as pd
from datetime import datetime

# Add current directory to path
sys.path.append(os.getcwd())

from GUI.data_manager import DataManager

def verify_hybrid_logic():
    print("🚀 Verifying Bithumb-Upbit Hybrid Logic...")
    dm = DataManager()
    
    # Test 1: Bithumb BTC (Should be redirected to Upbit and fetch > 200 candles)
    print("\n[TEST 1] Fetching Bithumb BTC (Target: 500 candles)")
    df = dm.download(symbol="BTC", exchange="bithumb", timeframe="1h", limit=500)
    
    if df is not None:
        print(f"✅ Received {len(df)} candles for Bithumb BTC.")
        if len(df) > 200:
            print("✨ SUCCESS: Redirection worked (Bithumb limit 200 bypassed via Upbit)")
        else:
            print("❌ FAILURE: Redirection might not have worked or data is scarce.")
    else:
        print("❌ FAILURE: Data fetch failed.")

    # Test 2: Bithumb STX (Common coin)
    print("\n[TEST 2] Fetching Bithumb STX (Common coin)")
    df_stx = dm.download(symbol="STX", exchange="bithumb", timeframe="1h", limit=300)
    if df_stx is not None:
         print(f"✅ Received {len(df_stx)} candles for Bithumb STX.")
    else:
         print("❌ FAILURE: STX fetch failed.")

if __name__ == "__main__":
    verify_hybrid_logic()
