# test_focused_grid.py - 중요 파라미터 중심 탐색 (240조합)

import sys
import os
import json
import itertools
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.strategy_core import AlphaX7Core
import pandas as pd
import numpy as np

print("=" * 60)
print("중요 파라미터 중심 탐색 (240조합)")
print("=" * 60)

# 데이터 로드
df_15m = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')

if 'timestamp' in df_15m.columns:
    if pd.api.types.is_numeric_dtype(df_15m['timestamp']):
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
    else:
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
    df_15m = df_15m.set_index('timestamp')

df_1h = df_15m.resample('1h').agg({
    'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
}).dropna().reset_index()
df_15m = df_15m.reset_index()

print(f"로드 데이터: 1h={len(df_1h)}개 ({len(df_1h)//24}일)")

# 핵심 파라미터 그리드
KEY_GRID = {
    'macd_fast': [6, 8, 10, 12],
    'macd_slow': [18, 20, 24, 28, 32],
    'atr_mult': [1.5, 1.8, 2.0, 2.2],
    'rsi_period': [14, 18, 21],
}

FIXED_PARAMS = {
    'macd_signal': 7,
    'ema_period': 10,
    'atr_period': 14,
    'trail_start_r': 0.8,
    'trail_dist_r': 0.5,
    'pullback_rsi_long': 45,
    'pullback_rsi_short': 55,
    'pattern_tolerance': 0.05,
    'entry_validity_hours': 48,
    'filter_tf': '4h',
}

def calc(trades, lev=3):
    if not trades:
        return {'trades': 0, 'win_rate': 0, 'simple': 0, 'mdd': 100}
    pnls = [float(str(t['pnl']).replace('%','')) * lev for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    equity, peak, max_dd = 100, 100, 0
    for p in pnls:
        equity *= (1 + p / 100)
        if equity > peak: peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd: max_dd = dd
    return {
        'trades': len(pnls),
        'win_rate': round(wins / len(pnls) * 100, 1) if pnls else 0,
        'simple': round(sum(pnls), 0),
        'mdd': round(max_dd, 1)
    }

all_keys = list(KEY_GRID.keys())
all_combinations = list(itertools.product(*[KEY_GRID[k] for k in all_keys]))
total = len(all_combinations)
print(f"총 조합 수: {total}개")

core = AlphaX7Core(use_mtf=True)
results = []
start_time = datetime.now()

for idx, combo in enumerate(all_combinations):
    params = dict(zip(all_keys, combo))
    params.update(FIXED_PARAMS)

    try:
        trades = core.run_backtest(df_pattern=df_1h, df_entry=df_15m, **params)
        m = calc(trades, lev=3)
        results.append({**params, **m})
    except Exception:
        pass

    if (idx + 1) % 50 == 0:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"진행: {idx+1}/{total} ({(idx+1)/total*100:.0f}%) | 경과: {elapsed:.0f}초")

output_path = 'config/optimization_results.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
safe_results = [r for r in results if r['mdd'] <= 20]
top_20 = sorted(safe_results, key=lambda x: x['simple'], reverse=True)[:20]

with open(output_path, 'w', encoding='utf-8') as f:
    json.dump({'timestamp': datetime.now().isoformat(), 'top_20': top_20}, f, indent=2, ensure_ascii=False)

print(f"탐색 완료! 결과 저장: {output_path}")
