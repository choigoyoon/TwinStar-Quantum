# test_full_grid.py - 전체 파라미터 그리드 탐색

import sys
import os
import itertools
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.strategy_core import AlphaX7Core
import pandas as pd

print("=" * 60)
print("전체 파라미터 그리드 탐색")
print("=" * 60)

df_15m = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
if 'timestamp' in df_15m.columns:
    df_15m = df_15m.set_index(pd.to_datetime(df_15m['timestamp'], unit='ms'))

df_1h = df_15m.resample('1h').agg({'open':'first', 'high':'max', 'low':'min', 'close':'last', 'volume':'sum'}).dropna().reset_index()
df_15m = df_15m.reset_index()

GRID = {
    'macd_fast': [8, 10, 12],
    'macd_slow': [26, 30, 34],
    'atr_mult': [1.8, 2.0, 2.2],
    'rsi_period': [14, 21]
}

all_keys = list(GRID.keys())
all_combinations = list(itertools.product(*[GRID[k] for k in all_keys]))
total = len(all_combinations)
print(f"전체 조합: {total}개")

core = AlphaX7Core(use_mtf=True)
for idx, combo in enumerate(all_combinations):
    params = dict(zip(all_keys, combo))
    # 탐색 생략 (컴파일 확인용)
    if (idx + 1) % 10 == 0:
        print(f"진행: {idx+1}/{total}")
