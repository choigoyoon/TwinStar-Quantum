"""
tools/test_priority3_simple.py
Priority 3 간단 검증: detect_wm_pattern_realtime() 기능 테스트

목적:
- detect_wm_pattern_realtime() 함수가 정상 작동하는지 확인
- 기본 기능 검증 (신호 생성, 파라미터 처리)
"""
import sys
from pathlib import Path
from collections import deque

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.incremental_indicators import IncrementalMACD

print("=" * 80)
print("Priority 3 간단 검증: detect_wm_pattern_realtime()")
print("=" * 80)

# 1. 데이터 로드
print("\n[1/3] 데이터 로드...")
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

print(f"[OK] 데이터: {len(df_1h):,}개 1h 캔들")

# 2. 최근 100개 데이터로 deque 버퍼 생성
print("\n[2/3] deque 버퍼 생성...")
strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

macd_buffer = deque(maxlen=100)
price_buffer = deque(maxlen=100)
timestamp_buffer = deque(maxlen=100)

# IncrementalMACD 초기화
incremental_macd = IncrementalMACD(fast=6, slow=18, signal=7)

# 최근 100개 데이터로 버퍼 초기화
recent_data = df_1h.tail(100)
for idx, row in recent_data.iterrows():
    close = row['close']
    result = incremental_macd.update(close)

    macd_buffer.append(result['histogram'])
    price_buffer.append({
        'high': row['high'],
        'low': row['low'],
        'close': close
    })
    timestamp_buffer.append(row['timestamp'])

print(f"[OK] 버퍼 초기화: {len(macd_buffer)}개")

# 3. detect_wm_pattern_realtime() 호출 테스트
print("\n[3/3] detect_wm_pattern_realtime() 호출...")

try:
    signal = strategy.detect_wm_pattern_realtime(
        macd_histogram_buffer=macd_buffer,
        price_buffer=price_buffer,
        timestamp_buffer=timestamp_buffer,
        pattern_tolerance=0.05,
        entry_validity_hours=48.0,
        filter_trend=None  # MTF 필터 비활성화
    )

    if signal:
        print(f"\n[OK] 신호 감지 성공!")
        print(f"  유형: {signal.signal_type}")
        print(f"  패턴: {signal.pattern}")
        print(f"  손절가: ${signal.stop_loss:,.2f}")
        print(f"  ATR: {signal.atr:.2f}")
    else:
        print("\n[OK] 신호 없음 (정상 동작)")

    print("\n" + "=" * 80)
    print("[SUCCESS] Priority 3 기능 검증 완료!")
    print("=" * 80)
    print("\ndetect_wm_pattern_realtime() 함수가 정상 작동합니다.")

except Exception as e:
    print(f"\n[FAIL] 에러 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
