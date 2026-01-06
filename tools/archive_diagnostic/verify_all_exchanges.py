from GUI.data_manager import DataManager
import os
import shutil

# Initialize
dm = DataManager()
print(f"Cache Dir: {dm.cache_dir}")

# Targets
targets = ['okx', 'bitget', 'bingx', 'bithumb', 'upbit', 'bybit', 'binance']
print(f"Testing {len(targets)} exchanges...")

success_count = 0
for ex in targets:
    try:
        sym = 'KRW-BTC' if ex in ['bithumb', 'upbit'] else 'BTCUSDT'
        
        # 1. Clear Cache
        for f in dm.cache_dir.glob(f'{ex}*.parquet'):
            try:
                os.remove(f)
            except:
                pass
                
        # 2. Download
        print(f"\n[{ex.upper()}] Downloading {sym}...")
        df = dm.download(sym, '15m', exchange=ex, limit=5)
        
        if len(df) > 0:
            print(f"✅ SUCCESS: {len(df)} rows")
            ts = df.iloc[0]['timestamp']
            print(f"   First TS: {ts} | Close: {df.iloc[0]['close']}")
            success_count += 1
        else:
            print(f"❌ FAILED: 0 rows")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

print(f"\nFinal Result: {success_count}/{len(targets)} working.")
