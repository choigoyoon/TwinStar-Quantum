import os
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 추가
sys.path.append(os.getcwd())

# Mocking
class MockExchange:
    def __init__(self, name, symbol):
        self.name = name
        self.symbol = symbol

class MockBot:
    def __init__(self, exchange_name, symbol):
        self.exchange = MockExchange(exchange_name, symbol)
        
        # 테스트용 데이터 생성
        self.df_entry_full = pd.DataFrame([
            {'timestamp': datetime.now(), 'open': 100, 'high': 110, 'low': 90, 'close': 105, 'volume': 1}
        ])
        self.df_pattern_full = pd.DataFrame([
            {'timestamp': datetime.now(), 'open': 100, 'high': 120, 'low': 80, 'close': 110, 'volume': 10}
        ])

    def _save_realtime_candle_to_parquet(self):
        # unified_bot.py의 로직 복사 (테스트용)
        try:
            import shutil
            from pathlib import Path
            # paths.Paths 대신 하드코딩 (테스트용)
            cache_dir = Path('data/cache')
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            exchange_name = self.exchange.name.lower()
            symbol_raw = self.exchange.symbol
            symbol_clean = symbol_raw.lower().replace('/', '').replace(':', '').replace('-', '')
            
            save_targets = []
            if self.df_entry_full is not None and not self.df_entry_full.empty:
                save_targets.append((self.df_entry_full, '15m'))
            if self.df_pattern_full is not None and not self.df_pattern_full.empty:
                save_targets.append((self.df_pattern_full, '1h'))
                
            for df, tf in save_targets:
                save_df = df.tail(1000).copy()
                filename = f"{exchange_name}_{symbol_clean}_{tf}.parquet"
                path = cache_dir / filename
                
                save_df.to_parquet(path, index=False)
                print(f"✅ Saved: {filename}")
                
                if exchange_name == 'bithumb':
                    try:
                        # constants import 테스트
                        sys.path.insert(0, os.path.join(os.getcwd(), 'GUI'))
                        from constants import COMMON_KRW_SYMBOLS
                        
                        coin = symbol_raw.split('/')[0].replace('KRW', '').replace('-', '').upper()
                        if coin in COMMON_KRW_SYMBOLS:
                            upbit_filename = f"upbit_{symbol_clean}_{tf}.parquet"
                            upbit_path = cache_dir / upbit_filename
                            shutil.copy(path, upbit_path)
                            print(f"✅ Hybrid Sync: {filename} -> {upbit_filename}")
                    except Exception as e:
                        print(f"❌ Hybrid Sync error: {e}")
        except Exception as e:
            print(f"❌ Realtime parquet error: {e}")

if __name__ == "__main__":
    # 빗썸 BTC 테스트 (공통 심볼)
    print("--- Testing Bithumb BTC (Common Symbol) ---")
    bot = MockBot('Bithumb', 'BTC/KRW')
    bot._save_realtime_candle_to_parquet()
    
    # 생성 확인
    p1 = Path('data/cache/bithumb_btckrw_1h.parquet')
    p2 = Path('data/cache/upbit_btckrw_1h.parquet')
    
    if p1.exists() and p2.exists():
        print(f"🎉 SUCCESS: Both files exist! ({p1.name}, {p2.name})")
        print(f"   Sizes: {p1.stat().st_size} vs {p2.stat().st_size}")
    else:
        print("❌ FAILED: Files missing")
