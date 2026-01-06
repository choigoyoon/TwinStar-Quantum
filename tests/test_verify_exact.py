# test_verify_exact.py - 정밀 로직 검증

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.strategy_core import AlphaX7Core
import pandas as pd

df_15m = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
print(f"데이터 로드 완료: {len(df_15m)}행")

print("정밀 검증 로직 가동...")
