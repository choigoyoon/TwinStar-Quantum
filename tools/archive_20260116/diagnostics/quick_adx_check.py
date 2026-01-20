#!/usr/bin/env python3
"""
ADX 전략 빠른 진단 - Exit code 49 회피용
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import pandas as pd
    import numpy as np
    from core.data_manager import BotDataManager
    from core.strategy_core import AlphaX7Core

    print("=" * 70)
    print("ADX 전략 빠른 진단")
    print("=" * 70)

    # 데이터 로드
    print("\n📂 데이터 로드 중...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    df = dm.get_full_history(with_indicators=False)

    if df is None or df.empty:
        print("❌ 데이터 없음")
        sys.exit(1)

    # 최근 100개만 사용 (빠른 분석)
    df = df.tail(100).copy()

    if 'timestamp' not in df.columns:
        print("❌ timestamp 컬럼 없음")
        sys.exit(1)

    if pd.api.types.is_numeric_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    else:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    print(f"✓ 데이터: {len(df)}개 캔들")

    # ADX 계산
    print("\n🔍 ADX 계산 중...")
    strategy = AlphaX7Core(strategy_type='adx')
    df_adx = strategy._calculate_adx_manual(df.copy(), period=14)

    adx_values: np.ndarray = np.asarray(df_adx['adx'].values, dtype=np.float64)  # type: ignore
    plus_di: np.ndarray = np.asarray(df_adx['plus_di'].values, dtype=np.float64)  # type: ignore
    minus_di: np.ndarray = np.asarray(df_adx['minus_di'].values, dtype=np.float64)  # type: ignore

    # 통계
    print("\n" + "─" * 70)
    print("ADX 통계 (마지막 100개 캔들)")
    print("─" * 70)

    valid_adx = adx_values[14:]  # 워밍업 제외

    print(f"\nADX 값:")
    print(f"  평균: {np.mean(valid_adx):.2f}")
    print(f"  최소: {np.min(valid_adx):.2f}")
    print(f"  최대: {np.max(valid_adx):.2f}")

    # ADX >= 25 비율
    strong_count = np.sum(valid_adx >= 25.0)
    strong_pct = strong_count / len(valid_adx) * 100

    print(f"\nADX >= 25 (강한 추세):")
    print(f"  캔들 수: {strong_count}개")
    print(f"  비율: {strong_pct:.1f}%")

    # DI 크로스오버 카운트
    crossovers = 0
    for i in range(15, len(df_adx)):
        if (plus_di[i-1] <= minus_di[i-1] and plus_di[i] > minus_di[i]) or \
           (minus_di[i-1] <= plus_di[i-1] and minus_di[i] > plus_di[i]):
            crossovers += 1

    crossover_pct = crossovers / len(valid_adx) * 100

    print(f"\nDI 크로스오버:")
    print(f"  횟수: {crossovers}회")
    print(f"  비율: {crossover_pct:.1f}%")

    # 신호 생성 가능 구간
    signal_eligible = 0
    for i in range(15, len(df_adx)):
        if adx_values[i] >= 25.0:
            if (plus_di[i-1] <= minus_di[i-1] and plus_di[i] > minus_di[i]) or \
               (minus_di[i-1] <= plus_di[i-1] and minus_di[i] > plus_di[i]):
                signal_eligible += 1

    signal_pct = signal_eligible / len(valid_adx) * 100

    print(f"\nADX >= 25 AND 크로스오버:")
    print(f"  신호 가능 구간: {signal_eligible}개")
    print(f"  비율: {signal_pct:.1f}%")

    # 진단
    print("\n" + "=" * 70)
    print("진단 결과")
    print("=" * 70)

    if strong_pct < 30:
        print(f"\n⚠️  ADX >= 25 구간이 {strong_pct:.1f}%로 낮음")
        print("   → 레인지/약한 추세 시장 지배적")
        print("   → 권장: ADX 임계값을 20 또는 18로 낮추기")

    if crossover_pct < 10:
        print(f"\n⚠️  DI 크로스오버가 {crossover_pct:.1f}%로 매우 낮음")
        print("   → 추세 전환이 드물거나 지속적 추세")
        print("   → 권장: ADX 기간을 10 또는 7로 단축")

    if signal_pct < 5:
        print(f"\n⚠️  신호 생성 가능 구간이 {signal_pct:.1f}%로 극히 낮음")
        print("   → 이중 필터(ADX + 크로스오버)가 너무 강함")
        print("   → 권장: 하이브리드 전략 (MACD + ADX 필터)")

    print("\n✓ 진단 완료")

except Exception as e:
    print(f"\n❌ 오류: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
