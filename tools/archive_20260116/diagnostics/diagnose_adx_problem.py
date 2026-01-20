#!/usr/bin/env python3
"""
ADX 문제 진단: DI 크로스오버 시점의 ADX 값 분포 분석
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.data_utils import resample_data


def main():
    print("="*70)
    print("ADX Problem Diagnosis: DI Crossover ADX Distribution")
    print("="*70)

    # 데이터 로드
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
    df_15m = dm.get_full_history(with_indicators=False)

    if df_15m is None or df_15m.empty:
        print("❌ 데이터 로드 실패")
        return 1

    df = resample_data(df_15m, '1h', add_indicators=False)

    print(f"Data: {len(df):,} candles\n")

    # ADX 계산
    strategy = AlphaX7Core(strategy_type='adx')
    df_with_adx = strategy._calculate_adx_manual(df, period=14)

    adx_values = df_with_adx['adx'].values
    plus_di = df_with_adx['plus_di'].values
    minus_di = df_with_adx['minus_di'].values

    # DI 크로스오버 감지
    crossovers = []

    for i in range(1, len(df_with_adx)):
        # +DI 상향 돌파 (Long)
        if plus_di[i-1] <= minus_di[i-1] and plus_di[i] > minus_di[i]:
            crossovers.append({
                'index': i,
                'time': df_with_adx.index[i],
                'type': 'Long',
                'adx': adx_values[i],
                'plus_di': plus_di[i],
                'minus_di': minus_di[i]
            })

        # -DI 상향 돌파 (Short)
        elif minus_di[i-1] <= plus_di[i-1] and minus_di[i] > plus_di[i]:
            crossovers.append({
                'index': i,
                'time': df_with_adx.index[i],
                'type': 'Short',
                'adx': adx_values[i],
                'plus_di': plus_di[i],
                'minus_di': minus_di[i]
            })

    print(f"Total DI Crossovers: {len(crossovers)}")
    print("-"*70)

    # ADX 값 분포
    adx_at_crossover = [c['adx'] for c in crossovers]

    print("\nADX Distribution at Crossover Points:")
    print("-"*70)
    print(f"Min:    {min(adx_at_crossover):.2f}")
    print(f"10%:    {np.percentile(adx_at_crossover, 10):.2f}")
    print(f"25%:    {np.percentile(adx_at_crossover, 25):.2f}")
    print(f"Median: {np.percentile(adx_at_crossover, 50):.2f}")
    print(f"75%:    {np.percentile(adx_at_crossover, 75):.2f}")
    print(f"90%:    {np.percentile(adx_at_crossover, 90):.2f}")
    print(f"Max:    {max(adx_at_crossover):.2f}")

    # Threshold별 필터링 결과
    print("\n" + "="*70)
    print("Signals Remaining by Threshold")
    print("="*70)

    thresholds = [5, 10, 15, 18, 20, 22, 25, 30]
    for threshold in thresholds:
        remaining = sum(1 for adx in adx_at_crossover if adx >= threshold)
        pct = (remaining / len(crossovers)) * 100
        print(f"Threshold {threshold:2}: {remaining:4} signals ({pct:5.1f}%)")

    # 샘플 크로스오버 출력
    print("\n" + "="*70)
    print("Sample Crossovers (First 10)")
    print("="*70)

    for i, c in enumerate(crossovers[:10], 1):
        print(f"\n{i}. {c['time']}")
        print(f"   Type: {c['type']}")
        print(f"   ADX: {c['adx']:.2f}")
        print(f"   +DI: {c['plus_di']:.2f}, -DI: {c['minus_di']:.2f}")
        print(f"   Pass Threshold 10: {'YES' if c['adx'] >= 10 else 'NO'}")
        print(f"   Pass Threshold 25: {'YES' if c['adx'] >= 25 else 'NO'}")

    # 결론
    print("\n" + "="*70)
    print("Diagnosis")
    print("="*70)

    median_adx = np.median(adx_at_crossover)
    p10_adx = np.percentile(adx_at_crossover, 10)

    if p10_adx > 25:
        print("FINDING: DI crossovers occur ONLY during strong trends")
        print(f"         -> 10th percentile ADX: {p10_adx:.2f} > 25")
        print(f"         -> Threshold 10/18/25 have SAME effect")
        print("\nIMPLICATION:")
        print("  - ADX threshold is NOT the limiting factor")
        print("  - DI crossover frequency is the bottleneck")
        print("  - To increase trades, need DIFFERENT strategy")
    elif median_adx < 18:
        print("FINDING: DI crossovers occur during weak trends")
        print(f"         -> Median ADX: {median_adx:.2f} < 18")
        print(f"         -> Threshold matters significantly")
    else:
        print("FINDING: Mixed ADX at crossovers")
        print(f"         -> Median ADX: {median_adx:.2f}")
        print(f"         -> Threshold has moderate impact")

    return 0


if __name__ == '__main__':
    sys.exit(main())
