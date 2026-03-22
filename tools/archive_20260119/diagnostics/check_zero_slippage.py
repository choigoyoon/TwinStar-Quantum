"""
슬리피지 0% 체결률 확인 (v7.24)
작성일: 2026-01-18

목적:
- 지정가 = next_open (프리미엄 0%)
- 체결 가능 여부 확인
- Long: next_low <= next_open?
- Short: next_high >= next_open?

실행:
python tools/check_zero_slippage.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from core.data_manager import BotDataManager
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def check_zero_slippage(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    entry_tf: str = '1h'
) -> dict:
    """
    슬리피지 0% (next_open 정확히) 체결 가능 여부 확인

    Args:
        exchange: 거래소
        symbol: 심볼
        entry_tf: 타임프레임

    Returns:
        dict: 체결률 통계
    """
    logger.info(f"슬리피지 0% 체결률 확인: {exchange} {symbol} {entry_tf}")

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

    # 2. 체결 여부 확인
    long_filled = 0
    long_failed = 0
    short_filled = 0
    short_failed = 0

    long_gaps = []
    short_gaps = []

    for i in range(len(df) - 1):
        next_open = df['open'].iloc[i + 1]
        next_low = df['low'].iloc[i + 1]
        next_high = df['high'].iloc[i + 1]

        # Long: next_open과 next_low 비교
        if next_low <= next_open:
            long_filled += 1
            gap_pct = (next_low - next_open) / next_open * 100
            long_gaps.append(gap_pct)
        else:
            long_failed += 1

        # Short: next_open과 next_high 비교
        if next_high >= next_open:
            short_filled += 1
            gap_pct = (next_high - next_open) / next_open * 100
            short_gaps.append(gap_pct)
        else:
            short_failed += 1

    # 3. 통계 계산
    total_candles = len(df) - 1
    long_fill_rate = (long_filled / total_candles * 100) if total_candles > 0 else 0
    short_fill_rate = (short_filled / total_candles * 100) if total_candles > 0 else 0

    long_gaps_arr = np.array(long_gaps)
    short_gaps_arr = np.array(short_gaps)

    # 4. 결과 출력
    print("\n" + "="*70)
    print("슬리피지 0% (next_open 정확히) 체결률 분석")
    print("="*70)
    print(f"거래소: {exchange}")
    print(f"심볼: {symbol}")
    print(f"타임프레임: {entry_tf}")
    print(f"분석 봉 수: {total_candles:,}개")
    print("="*70)

    print("\n[Long 진입 (지정가 = next_open)]")
    print("-"*70)
    print(f"체결 가능:   {long_filled:,}개 ({long_fill_rate:.2f}%)")
    print(f"미체결:       {long_failed:,}개 ({100-long_fill_rate:.2f}%)")
    print()
    print(f"갭 통계 (next_low - next_open):")
    print(f"  평균:       {np.mean(long_gaps_arr):.3f}%")
    print(f"  중간값:     {np.median(long_gaps_arr):.3f}%")
    print(f"  최소:       {np.min(long_gaps_arr):.3f}%")
    print(f"  최대:       {np.max(long_gaps_arr):.3f}%")
    print("="*70)

    print("\n[Short 진입 (지정가 = next_open)]")
    print("-"*70)
    print(f"체결 가능:   {short_filled:,}개 ({short_fill_rate:.2f}%)")
    print(f"미체결:       {short_failed:,}개 ({100-short_fill_rate:.2f}%)")
    print()
    print(f"갭 통계 (next_high - next_open):")
    print(f"  평균:       {np.mean(short_gaps_arr):.3f}%")
    print(f"  중간값:     {np.median(short_gaps_arr):.3f}%")
    print(f"  최소:       {np.min(short_gaps_arr):.3f}%")
    print(f"  최대:       {np.max(short_gaps_arr):.3f}%")
    print("="*70)

    # 5. 평균 체결률
    avg_fill_rate = (long_fill_rate + short_fill_rate) / 2

    print("\n[평균 체결률]")
    print("-"*70)
    print(f"Long + Short 평균: {avg_fill_rate:.2f}%")
    print("="*70)

    # 6. 해석
    print("\n[해석]")
    print("-"*70)
    if avg_fill_rate >= 95:
        print("결론: 슬리피지 0%로도 거의 100% 체결 가능!")
        print("      지정가 = next_open 사용 권장")
        print("      수수료만 0.02% 적용하면 됨")
    elif avg_fill_rate >= 90:
        print("결론: 슬리피지 0%로 90% 이상 체결 가능")
        print("      작은 프리미엄 (+0.01%) 추가 시 안정적")
    elif avg_fill_rate >= 75:
        print("결론: 슬리피지 0%로 75% 이상 체결 가능")
        print("      프리미엄 +0.042% (Long) / -0.247% (Short) 권장")
    else:
        print("결론: 슬리피지 0%는 체결률 낮음")
        print("      프리미엄 필수")
    print("="*70)

    return {
        'long_fill_rate': long_fill_rate,
        'long_filled': long_filled,
        'long_failed': long_failed,
        'short_fill_rate': short_fill_rate,
        'short_filled': short_filled,
        'short_failed': short_failed,
        'avg_fill_rate': avg_fill_rate,
        'long_gaps': long_gaps_arr.tolist(),
        'short_gaps': short_gaps_arr.tolist()
    }


if __name__ == '__main__':
    result = check_zero_slippage(
        exchange='bybit',
        symbol='BTCUSDT',
        entry_tf='1h'
    )

    print("\n\n[RESULT] 최종 결론:")
    print(f"슬리피지 0% 평균 체결률: {result.get('avg_fill_rate', 0):.2f}%")
    print(f"Long: {result.get('long_fill_rate', 0):.2f}%")
    print(f"Short: {result.get('short_fill_rate', 0):.2f}%")
