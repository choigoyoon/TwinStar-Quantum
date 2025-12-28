import sys
import os
import pandas as pd
from pathlib import Path

# Add current directory to path
sys.path.append(os.getcwd())

from GUI.data_manager import DataManager

def verify_dual_saving():
    print("🚀 Verifying Bithumb-Upbit Dual-Saving Logic...")
    dm = DataManager()
    
    # Define paths
    upbit_path = dm._get_cache_path('upbit', 'BTC', '1h')
    bithumb_path = dm._get_cache_path('bithumb', 'BTC', '1h')
    
    # Remove existing files for a clean test
    if upbit_path.exists(): os.remove(upbit_path)
    if bithumb_path.exists(): os.remove(bithumb_path)
    
    print(f"\n[TEST] Downloading Upbit BTC (100 candles)...")
    df = dm.download(symbol="BTC", exchange="upbit", timeframe="1h", limit=100)
    
    if df is not None:
        print(f"✅ Downloaded {len(df)} candles.")
        
        if upbit_path.exists():
            print(f"📂 Upbit cache created: {upbit_path.name}")
        else:
            print("❌ Upbit cache NOT created.")
            
        if bithumb_path.exists():
            print(f"📂 Bithumb cache created via DUAL-SAVING: {bithumb_path.name}")
            # Verify contents
            df_bithumb = pd.read_parquet(bithumb_path)
            if len(df_bithumb) == len(df):
                print(f"✨ SUCCESS: Bithumb cache matches Upbit data ({len(df_bithumb)} candles)")
            else:
                print(f"❌ FAILURE: Bithumb cache size mismatch ({len(df_bithumb)} vs {len(df)})")
        else:
            print("❌ FAILURE: Bithumb cache NOT created.")
    else:
        print("❌ Download failed.")

if __name__ == "__main__":
    verify_dual_saving()
