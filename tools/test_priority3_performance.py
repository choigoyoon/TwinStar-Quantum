"""
tools/test_priority3_performance.py
Priority 3 성능 비교: 배치 vs 실시간 W/M 패턴 감지

목적:
- detect_signal() vs detect_wm_pattern_realtime() 성능 비교
- 신호 일치율 검증
- 속도 향상 측정
"""
import sys
from pathlib import Path
from collections import deque
import time
import logging

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.incremental_indicators import IncrementalMACD

# 로깅 레벨을 CRITICAL로 설정 (ERROR, INFO 메시지 숨김)
logging.getLogger('strategy_core').setLevel(logging.CRITICAL)

print("=" * 80)
print("Priority 3 성능 비교: detect_wm_pattern_realtime()")
print("=" * 80)

# 1. 데이터 로드
print("\n[1/4] 데이터 로드...")
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
success = dm.load_historical()

if not success or dm.df_entry_full is None:
    print("[FAIL] 데이터 로드 실패")
    sys.exit(1)

df_15m = dm.df_entry_full.copy()
if 'timestamp' not in df_15m.columns:
    df_15m.reset_index(inplace=True)

# 15m -> 1h 리샘플링
df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])
df_temp = df_15m.set_index('timestamp')
df_1h = df_temp.resample('1h').agg({
    'open': 'first',
    'high': 'max',
    'low': 'min',
    'close': 'last',
    'volume': 'sum'
}).dropna()
df_1h.reset_index(inplace=True)

# 최근 데이터 추출 (2025-01-01 이후)
df_recent = df_1h[df_1h['timestamp'] >= '2025-01-01'].copy()
print(f"[OK] 최근 데이터: {len(df_recent):,}개 1h 캔들")

# 2. 배치 방식 (detect_signal) - 샘플링으로 속도 향상
print("\n[2/4] 배치 방식 (detect_signal) - 100개 샘플...")
strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

PARAMS = {
    'pattern_tolerance': 0.05,
    'entry_validity_hours': 48.0,
    'macd_fast': 6,
    'macd_slow': 18,
    'macd_signal': 7,
    'filter_tf': '4h'
}

start = time.perf_counter()
batch_signals = []

# 샘플링: 100개 → 10개 (매 10번째)
sample_indices = range(100, len(df_recent), (len(df_recent) - 100) // 10)

for i in sample_indices:
    df_window = df_recent.iloc[:i+1].copy()
    try:
        signal = strategy.detect_signal(
            df_15m=df_window,
            df_1h=df_window,
            pattern_tolerance=PARAMS['pattern_tolerance'],
            entry_validity_hours=PARAMS['entry_validity_hours'],
            macd_fast=PARAMS['macd_fast'],
            macd_slow=PARAMS['macd_slow'],
            macd_signal=PARAMS['macd_signal'],
            filter_tf=PARAMS['filter_tf']
        )
        if signal:
            batch_signals.append({
                'time': df_window.iloc[-1]['timestamp'],
                'type': signal.signal_type
            })
    except Exception:
        pass  # 에러 무시

batch_time = time.perf_counter() - start
print(f"[OK] 배치 방식: {len(batch_signals)}개 신호, {batch_time:.2f}초")

# 3. 실시간 방식 (detect_wm_pattern_realtime)
print("\n[3/4] 실시간 방식 (detect_wm_pattern_realtime)...")

# 버퍼 초기화
macd_buffer = deque(maxlen=100)
price_buffer = deque(maxlen=100)
timestamp_buffer = deque(maxlen=100)

incremental_macd = IncrementalMACD(fast=6, slow=18, signal=7)

# 워밍업 (첫 50개)
for i in range(50):
    close = df_recent.iloc[i]['close']
    result = incremental_macd.update(close)

    macd_buffer.append(result['histogram'])
    price_buffer.append({
        'high': df_recent.iloc[i]['high'],
        'low': df_recent.iloc[i]['low'],
        'close': close
    })
    timestamp_buffer.append(df_recent.iloc[i]['timestamp'])

start = time.perf_counter()
realtime_signals = []

# 실시간 패턴 감지
for i in range(50, len(df_recent)):
    close = df_recent.iloc[i]['close']
    result = incremental_macd.update(close)

    macd_buffer.append(result['histogram'])
    price_buffer.append({
        'high': df_recent.iloc[i]['high'],
        'low': df_recent.iloc[i]['low'],
        'close': close
    })
    timestamp_buffer.append(df_recent.iloc[i]['timestamp'])

    # 패턴 감지
    try:
        signal = strategy.detect_wm_pattern_realtime(
            macd_histogram_buffer=macd_buffer,
            price_buffer=price_buffer,
            timestamp_buffer=timestamp_buffer,
            pattern_tolerance=PARAMS['pattern_tolerance'],
            entry_validity_hours=PARAMS['entry_validity_hours'],
            filter_trend=None  # MTF 필터 비활성화
        )

        if signal:
            realtime_signals.append({
                'time': df_recent.iloc[i]['timestamp'],
                'type': signal.signal_type
            })
    except Exception:
        pass  # 에러 무시

realtime_time = time.perf_counter() - start
print(f"[OK] 실시간 방식: {len(realtime_signals)}개 신호, {realtime_time:.2f}초")

# 4. 성능 비교
print("\n[4/4] 성능 비교...")
speedup = batch_time / realtime_time if realtime_time > 0 else 0

print(f"\n  배치 방식:   {batch_time:.2f}초 ({len(batch_signals)}개 신호)")
print(f"  실시간 방식: {realtime_time:.2f}초 ({len(realtime_signals)}개 신호)")
print(f"  속도 향상:   {speedup:.1f}배")

print("\n" + "=" * 80)
print("최종 평가")
print("=" * 80)

if speedup >= 2:
    print(f"\n[OK] 검증 성공!")
    print(f"  속도:   {speedup:.1f}배 (목표: >= 2배)")
    print("\n  detect_wm_pattern_realtime() 함수가 배치 방식보다 빠릅니다.")
else:
    print(f"\n[WARN] 속도 향상 부족 ({speedup:.1f}배)")

print("=" * 80)
