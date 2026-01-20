"""
tools/test_realtime_wm_pattern.py
실시간 W/M 패턴 감지 함수 테스트 (v7.27)

목적:
- detect_wm_pattern_realtime() 함수 검증
- 백테스트 check_signal()과 동일한 결과 생성하는지 확인
- deque 기반 실시간 패턴 감지 성능 측정
"""
import sys
from pathlib import Path
import time
from collections import deque

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.incremental_indicators import IncrementalMACD

print("=" * 80)
print("실시간 W/M 패턴 감지 테스트 (v7.27)")
print("=" * 80)

# 1단계: 데이터 로드
print("\n[1/5] 데이터 로드 중...")
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
success = dm.load_historical()

if not success or dm.df_entry_full is None:
    print("[FAIL] 데이터 로드 실패")
    sys.exit(1)

# 15m -> 1h 리샘플링
df_15m = dm.df_entry_full.copy()
if 'timestamp' not in df_15m.columns:
    df_15m.reset_index(inplace=True)

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

print(f"[OK] 데이터: {len(df_1h):,}개 1h 캔들")

# 2단계: 최근 데이터 추출 (2025-01-01 이후)
print("\n[2/5] 최근 데이터 추출 (2025-01-01 이후)...")
df_recent = df_1h[df_1h['timestamp'] >= '2025-01-01'].copy()

if len(df_recent) == 0:
    print("[FAIL] 2025-01-01 이후 데이터 없음")
    sys.exit(1)

print(f"[OK] 최근 데이터: {len(df_recent):,}개 1h 캔들")

# 3단계: 배치 방식 (check_signal) vs 실시간 방식 비교
print("\n[3/5] 배치 vs 실시간 패턴 감지 비교...")

strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

# v7.27 파라미터
PARAMS = {
    'pattern_tolerance': 0.05,
    'entry_validity_hours': 48.0,
    'macd_fast': 6,
    'macd_slow': 18,
    'macd_signal': 7,
    'filter_tf': '4h'
}

# 3-1. 배치 방식 (detect_signal)
print("\n  [3-1] 배치 방식 (detect_signal)...")
start = time.perf_counter()

batch_signals = []
for i in range(100, len(df_recent)):
    df_window = df_recent.iloc[:i+1].copy()
    signal = strategy.detect_signal(
        df_15m=df_window,  # 실제로는 1h 데이터 사용
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
            'type': signal.signal_type,
            'pattern': signal.pattern,
            'price': df_window.iloc[-1]['close'],
            'stop_loss': signal.stop_loss
        })

batch_time = time.perf_counter() - start
print(f"  [OK] 배치 방식: {len(batch_signals)}개 신호, {batch_time:.2f}초")

# 3-2. 실시간 방식 (detect_wm_pattern_realtime)
print("\n  [3-2] 실시간 방식 (detect_wm_pattern_realtime)...")
start = time.perf_counter()

# 버퍼 초기화
macd_buffer = deque(maxlen=100)
price_buffer = deque(maxlen=100)
timestamp_buffer = deque(maxlen=100)

# IncrementalMACD 초기화
incremental_macd = IncrementalMACD(
    fast=PARAMS['macd_fast'],
    slow=PARAMS['macd_slow'],
    signal=PARAMS['macd_signal']
)

# 워밍업 (첫 50개 데이터로 MACD 초기화)
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

# 실시간 패턴 감지 (50번째 이후)
realtime_signals = []
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
    signal = strategy.detect_wm_pattern_realtime(
        macd_histogram_buffer=macd_buffer,
        price_buffer=price_buffer,
        timestamp_buffer=timestamp_buffer,
        pattern_tolerance=PARAMS['pattern_tolerance'],
        entry_validity_hours=PARAMS['entry_validity_hours'],
        filter_trend=None  # MTF 필터 비활성화 (간단히 테스트)
    )

    if signal:
        realtime_signals.append({
            'time': df_recent.iloc[i]['timestamp'],
            'type': signal.signal_type,
            'pattern': signal.pattern,
            'price': df_recent.iloc[i]['close'],
            'stop_loss': signal.stop_loss
        })

realtime_time = time.perf_counter() - start
print(f"  [OK] 실시간 방식: {len(realtime_signals)}개 신호, {realtime_time:.2f}초")

# 4단계: 성능 비교
print("\n[4/5] 성능 비교...")
speedup = batch_time / realtime_time if realtime_time > 0 else 0

print(f"\n  배치 방식:   {batch_time:.2f}초 ({len(batch_signals)}개 신호)")
print(f"  실시간 방식: {realtime_time:.2f}초 ({len(realtime_signals)}개 신호)")
print(f"  속도 향상:   {speedup:.1f}배")

# 5단계: 신호 일치도 확인
print("\n[5/5] 신호 일치도 확인...")

# 타임스탬프 기준으로 신호 비교
batch_times = {s['time']: s for s in batch_signals}
realtime_times = {s['time']: s for s in realtime_signals}

common_times = set(batch_times.keys()) & set(realtime_times.keys())
batch_only = set(batch_times.keys()) - set(realtime_times.keys())
realtime_only = set(realtime_times.keys()) - set(batch_times.keys())

match_rate = len(common_times) / len(batch_times) * 100 if len(batch_times) > 0 else 0

print(f"\n  공통 신호:      {len(common_times)}개")
print(f"  배치 전용:      {len(batch_only)}개")
print(f"  실시간 전용:    {len(realtime_only)}개")
print(f"  일치율:         {match_rate:.1f}%")

# 공통 신호의 가격/SL 일치도 확인
if len(common_times) > 0:
    price_diffs = []
    sl_diffs = []

    for t in common_times:
        batch_sig = batch_times[t]
        realtime_sig = realtime_times[t]

        price_diff = abs(batch_sig['price'] - realtime_sig['price']) / batch_sig['price'] * 100
        sl_diff = abs(batch_sig['stop_loss'] - realtime_sig['stop_loss']) / batch_sig['stop_loss'] * 100

        price_diffs.append(price_diff)
        sl_diffs.append(sl_diff)

    avg_price_diff = np.mean(price_diffs)
    avg_sl_diff = np.mean(sl_diffs)

    print(f"\n  가격 차이 (평균): {avg_price_diff:.4f}%")
    print(f"  SL 차이 (평균):   {avg_sl_diff:.4f}%")

    if avg_price_diff < 0.01 and avg_sl_diff < 0.01:
        print("  [OK] 가격/SL 거의 동일 (< 0.01%)")
    else:
        print("  [WARN] 가격/SL 차이 있음")

# 최종 평가
print("\n" + "=" * 80)
print("최종 평가")
print("=" * 80)

if match_rate >= 80 and speedup >= 2:
    print(f"\n[OK] 검증 성공!")
    print(f"  일치율: {match_rate:.1f}% (목표: >= 80%)")
    print(f"  속도:   {speedup:.1f}배 (목표: >= 2배)")
    print("\n  detect_wm_pattern_realtime() 함수가 check_signal()과 일관된 결과를 생성합니다.")
elif match_rate >= 80:
    print(f"\n[WARN] 일치율은 OK ({match_rate:.1f}%), 속도 향상 부족 ({speedup:.1f}배)")
elif speedup >= 2:
    print(f"\n[WARN] 속도는 OK ({speedup:.1f}배), 일치율 부족 ({match_rate:.1f}%)")
else:
    print(f"\n[FAIL] 검증 실패!")
    print(f"  일치율: {match_rate:.1f}% (목표: >= 80%)")
    print(f"  속도:   {speedup:.1f}배 (목표: >= 2배)")

print("=" * 80)
