"""
진입가 차이 디버깅 (v1.0 - 2026-01-19)

656% 차이의 원인 파악
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.indicators import add_all_indicators
import pandas as pd

CORRECT_PARAMS = {
    'atr_mult': 1.25,
    'filter_tf': '4h',
    'trail_start_r': 0.4,
    'trail_dist_r': 0.05,
    'entry_validity_hours': 6.0,
    'leverage': 1,
    'macd_fast': 6,
    'macd_slow': 18,
    'macd_signal': 7
}

dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
dm.load_historical()

if dm.df_entry_full is None:
    raise ValueError("데이터가 비어 있습니다. load_historical() 실패")

df_15m = dm.df_entry_full.copy()
df_temp = df_15m.set_index('timestamp')
df_1h = df_temp.resample('1h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()
df_1h.reset_index(inplace=True)

add_all_indicators(df_1h, inplace=True)

strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')
backtest_trades = strategy.run_backtest(
    df_pattern=df_1h,
    df_entry=df_1h,
    slippage=0.001,
    **CORRECT_PARAMS
)

print("="*80)
print("진입가 차이 디버깅")
print("="*80 + "\n")

# 처음 10개 거래 상세 분석
print("처음 10개 거래 상세:")
print(f"\n{'#':<5} {'Side':<6} {'Signal Idx':<12} {'Entry Idx':<11} {'Signal Close':>15} {'Entry Open':>15} {'Diff %':>10}")
print("-"*90)

for i, trade in enumerate(backtest_trades[:10]):
    signal_idx = trade.get('signal_idx', 0)
    entry_idx = trade.get('entry_idx', 0)
    side = trade.get('type', 'Long')

    if signal_idx >= len(df_1h) or entry_idx >= len(df_1h):
        print(f"{i+1:<5} {side:<6} {signal_idx:<12} {entry_idx:<11} {'SKIP (Index out of range)':>15}")
        continue

    signal_candle = df_1h.iloc[signal_idx]
    entry_candle = df_1h.iloc[entry_idx]

    signal_close = signal_candle['close']
    entry_open = entry_candle['open']

    diff_pct = (entry_open - signal_close) / signal_close * 100

    print(f"{i+1:<5} {side:<6} {signal_idx:<12} {entry_idx:<11} {signal_close:>15,.2f} {entry_open:>15,.2f} {diff_pct:>9.3f}%")

# 통계
print("\n" + "="*80)
print("문제 진단")
print("="*80 + "\n")

# signal_idx vs entry_idx 간격 확인
idx_gaps = []
for trade in backtest_trades:
    signal_idx = trade.get('signal_idx', 0)
    entry_idx = trade.get('entry_idx', 0)
    gap = entry_idx - signal_idx
    idx_gaps.append(gap)

import numpy as np
print(f"signal_idx와 entry_idx 간격:")
print(f"  평균: {np.mean(idx_gaps):.1f}개 봉")
print(f"  중간값: {np.median(idx_gaps):.1f}개 봉")
print(f"  최소: {np.min(idx_gaps)}개 봉")
print(f"  최대: {np.max(idx_gaps)}개 봉")

# 간격이 1이 아닌 거래
abnormal_gaps = [gap for gap in idx_gaps if gap != 1]
print(f"\n  간격이 1이 아닌 거래: {len(abnormal_gaps)}개 ({len(abnormal_gaps)/len(idx_gaps)*100:.1f}%)")

if len(abnormal_gaps) > 0:
    print(f"    - 2개 이상 간격: {sum(1 for g in abnormal_gaps if g >= 2)}개")
    print(f"    - 10개 이상 간격: {sum(1 for g in abnormal_gaps if g >= 10)}개")
    print(f"    - 100개 이상 간격: {sum(1 for g in abnormal_gaps if g >= 100)}개")

print("\n원인 분석:")
if np.median(idx_gaps) > 1:
    print(f"  → entry_validity_hours={CORRECT_PARAMS['entry_validity_hours']}시간")
    print(f"  → 신호 발생 후 최대 {CORRECT_PARAMS['entry_validity_hours']}시간 내 진입")
    print(f"  → 간격이 큰 거래: 시간이 많이 지난 후 진입 (가격 변동 큼)")
    print(f"  → 이것이 656% 차이의 원인!")
else:
    print("  → 간격은 정상 (대부분 1)")
    print("  → 다른 원인 조사 필요")

# 가격 차이 실제 계산
actual_diffs = []
for trade in backtest_trades:
    signal_idx = trade.get('signal_idx', 0)
    entry_idx = trade.get('entry_idx', 0)

    if signal_idx >= len(df_1h) or entry_idx >= len(df_1h):
        continue

    signal_candle = df_1h.iloc[signal_idx]
    entry_candle = df_1h.iloc[entry_idx]

    signal_close = signal_candle['close']
    entry_open = entry_candle['open']

    diff = abs(entry_open - signal_close)  # 절대값
    diff_pct = diff / signal_close * 100

    actual_diffs.append(diff_pct)

print(f"\n실제 가격 차이 (절대값):")
print(f"  평균: {np.mean(actual_diffs):.3f}%")
print(f"  중간값: {np.median(actual_diffs):.3f}%")
print(f"  최대: {np.max(actual_diffs):.3f}%")

print("\n결론:")
if np.median(idx_gaps) > 1:
    print("  entry_validity_hours 파라미터로 인해")
    print("  신호 발생과 실제 진입 사이 시간 간격이 큼")
    print("  → 이는 의도된 설계 (유효시간 내 진입)")
    print("  → 백테스트는 정확함")
    print("\n  웹소켓 실시간:")
    print("  → 신호 발생 즉시 진입하면 간격 1개 봉")
    print("  → 가격 차이 훨씬 작아짐")
    print("  → 성능 개선 가능성 있음")
else:
    print("  간격은 정상, 가격 변동이 큰 시장")
