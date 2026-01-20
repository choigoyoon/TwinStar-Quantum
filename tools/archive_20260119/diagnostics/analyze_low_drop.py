"""
다음 봉 Low 하락폭 분석 (v7.24)
작성일: 2026-01-18

목적:
- 다음 봉 Low가 Open 대비 평균/중간값/백분위수로 얼마나 하락하는지 분석
- 최적의 지정가 프리미엄 결정

실행:
python tools/analyze_low_drop.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from core.data_manager import BotDataManager
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def analyze_low_drop(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    entry_tf: str = '1h'
) -> dict:
    """
    다음 봉 Low의 Open 대비 하락폭 분석

    Args:
        exchange: 거래소
        symbol: 심볼
        entry_tf: 타임프레임

    Returns:
        dict: 통계 정보
    """
    logger.info(f"Low 하락폭 분석 시작: {exchange} {symbol} {entry_tf}")

    # 1. 데이터 로드
    dm = BotDataManager(exchange, symbol, {'entry_tf': entry_tf})
    dm.load_historical()

    if dm.df_entry_full is None:
        logger.error("데이터 부족")
        return {}

    df = dm.df_entry_full.copy()

    if len(df) < 100:
        logger.error("데이터 부족")
        return {}

    logger.info(f"데이터: {len(df):,}개 봉")

    # 2. 다음 봉 Low/High 대비 Open 하락/상승폭 계산
    low_drops = []  # (next_low - next_open) / next_open * 100
    high_rises = []  # (next_high - next_open) / next_open * 100

    for i in range(len(df) - 1):
        next_open = df['open'].iloc[i + 1]
        next_low = df['low'].iloc[i + 1]
        next_high = df['high'].iloc[i + 1]

        # Low 하락폭 (음수 = 하락)
        low_drop_pct = (next_low - next_open) / next_open * 100
        low_drops.append(low_drop_pct)

        # High 상승폭 (양수 = 상승)
        high_rise_pct = (next_high - next_open) / next_open * 100
        high_rises.append(high_rise_pct)

    # 3. 통계 계산
    low_drops_arr = np.array(low_drops)
    high_rises_arr = np.array(high_rises)

    stats = {
        # Low 하락 통계
        'low_mean': np.mean(low_drops_arr),
        'low_median': np.median(low_drops_arr),
        'low_std': np.std(low_drops_arr),
        'low_min': np.min(low_drops_arr),
        'low_max': np.max(low_drops_arr),
        'low_p10': np.percentile(low_drops_arr, 10),
        'low_p25': np.percentile(low_drops_arr, 25),
        'low_p50': np.percentile(low_drops_arr, 50),
        'low_p75': np.percentile(low_drops_arr, 75),
        'low_p90': np.percentile(low_drops_arr, 90),
        'low_p95': np.percentile(low_drops_arr, 95),
        'low_p99': np.percentile(low_drops_arr, 99),

        # High 상승 통계
        'high_mean': np.mean(high_rises_arr),
        'high_median': np.median(high_rises_arr),
        'high_std': np.std(high_rises_arr),
        'high_min': np.min(high_rises_arr),
        'high_max': np.max(high_rises_arr),
        'high_p10': np.percentile(high_rises_arr, 10),
        'high_p25': np.percentile(high_rises_arr, 25),
        'high_p50': np.percentile(high_rises_arr, 50),
        'high_p75': np.percentile(high_rises_arr, 75),
        'high_p90': np.percentile(high_rises_arr, 90),
        'high_p95': np.percentile(high_rises_arr, 95),
        'high_p99': np.percentile(high_rises_arr, 99),
    }

    # 4. 결과 출력
    print("\n" + "="*70)
    print("다음 봉 Low/High 변동폭 분석 (Open 기준)")
    print("="*70)
    print(f"거래소: {exchange}")
    print(f"심볼: {symbol}")
    print(f"타임프레임: {entry_tf}")
    print(f"데이터 기간: {df.index[0]} ~ {df.index[-1]}")
    print(f"분석 봉 수: {len(low_drops):,}개")
    print("="*70)

    print("\n[LOW 하락폭 통계] (음수 = 하락)")
    print("-"*70)
    print(f"평균 (Mean):        {stats['low_mean']:.3f}%")
    print(f"중간값 (Median):    {stats['low_median']:.3f}%")
    print(f"표준편차 (Std):     {stats['low_std']:.3f}%")
    print(f"최소값 (Min):       {stats['low_min']:.3f}%")
    print(f"최대값 (Max):       {stats['low_max']:.3f}%")
    print("-"*70)
    print("백분위수 (Percentile):")
    print(f"  10%: {stats['low_p10']:.3f}%")
    print(f"  25%: {stats['low_p25']:.3f}%")
    print(f"  50%: {stats['low_p50']:.3f}%  (중간값)")
    print(f"  75%: {stats['low_p75']:.3f}%")
    print(f"  90%: {stats['low_p90']:.3f}%")
    print(f"  95%: {stats['low_p95']:.3f}%")
    print(f"  99%: {stats['low_p99']:.3f}%")
    print("="*70)

    print("\n[HIGH 상승폭 통계] (양수 = 상승)")
    print("-"*70)
    print(f"평균 (Mean):        {stats['high_mean']:.3f}%")
    print(f"중간값 (Median):    {stats['high_median']:.3f}%")
    print(f"표준편차 (Std):     {stats['high_std']:.3f}%")
    print(f"최소값 (Min):       {stats['high_min']:.3f}%")
    print(f"최대값 (Max):       {stats['high_max']:.3f}%")
    print("-"*70)
    print("백분위수 (Percentile):")
    print(f"  10%: {stats['high_p10']:.3f}%")
    print(f"  25%: {stats['high_p25']:.3f}%")
    print(f"  50%: {stats['high_p50']:.3f}%  (중간값)")
    print(f"  75%: {stats['high_p75']:.3f}%")
    print(f"  90%: {stats['high_p90']:.3f}%")
    print(f"  95%: {stats['high_p95']:.3f}%")
    print(f"  99%: {stats['high_p99']:.3f}%")
    print("="*70)

    # 5. 지정가 프리미엄 권장사항
    print("\n[지정가 프리미엄 권장사항]")
    print("-"*70)

    # Long 진입: Open 대비 Low가 평균적으로 얼마나 하락?
    # 예: Low 평균 -0.5% → 지정가 +0.5% 설정 시 평균적으로 체결
    long_premium_avg = -stats['low_mean']  # 음수를 양수로 변환
    long_premium_50 = -stats['low_p50']
    long_premium_75 = -stats['low_p75']
    long_premium_90 = -stats['low_p90']

    print(f"Long 진입 (Open 대비 위로 프리미엄):")
    print(f"  평균 체결:    +{long_premium_avg:.3f}%")
    print(f"  50% 체결:     +{long_premium_50:.3f}%")
    print(f"  75% 체결:     +{long_premium_75:.3f}%")
    print(f"  90% 체결:     +{long_premium_90:.3f}%")
    print()

    # Short 진입: Open 대비 High가 평균적으로 얼마나 상승?
    short_premium_avg = stats['high_mean']
    short_premium_50 = stats['high_p50']
    short_premium_75 = stats['high_p75']
    short_premium_90 = stats['high_p90']

    print(f"Short 진입 (Open 대비 아래로 프리미엄):")
    print(f"  평균 체결:    -{short_premium_avg:.3f}%")
    print(f"  50% 체결:     -{short_premium_50:.3f}%")
    print(f"  75% 체결:     -{short_premium_75:.3f}%")
    print(f"  90% 체결:     -{short_premium_90:.3f}%")
    print("="*70)

    # 6. 최종 권장
    print("\n[RESULT] 최종 권장:")
    print("-"*70)

    # 중간값 기준 (50% 체결)
    print(f"1. 보수적 (50% 체결):")
    print(f"   Long:  Open x (1 + {long_premium_50/100:.5f}) = Open x {1 + long_premium_50/100:.5f}")
    print(f"   Short: Open x (1 - {short_premium_50/100:.5f}) = Open x {1 - short_premium_50/100:.5f}")
    print()

    # 75% 체결
    print(f"2. 권장 (75% 체결):")
    print(f"   Long:  Open x (1 + {long_premium_75/100:.5f}) = Open x {1 + long_premium_75/100:.5f}")
    print(f"   Short: Open x (1 - {short_premium_75/100:.5f}) = Open x {1 - short_premium_75/100:.5f}")
    print()

    # 90% 체결
    print(f"3. 공격적 (90% 체결):")
    print(f"   Long:  Open x (1 + {long_premium_90/100:.5f}) = Open x {1 + long_premium_90/100:.5f}")
    print(f"   Short: Open x (1 - {short_premium_90/100:.5f}) = Open x {1 - short_premium_90/100:.5f}")
    print("="*70)

    return stats


if __name__ == '__main__':
    # Bybit BTC/USDT 1h
    stats = analyze_low_drop(
        exchange='bybit',
        symbol='BTCUSDT',
        entry_tf='1h'
    )
