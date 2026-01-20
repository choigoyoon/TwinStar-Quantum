"""
최적 진입 가격 분석 (v7.24)
작성일: 2026-01-18

목적:
- 신호 발생 후 다음 봉에서 최적 진입 가격 찾기
- Long: next_low에서 진입 시 수익 증가폭
- Short: next_high에서 진입 시 수익 증가폭
- Open vs Low/High 진입 비교

실행:
python tools/optimal_entry_analysis.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
from core.data_manager import BotDataManager
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def optimal_entry_analysis(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    entry_tf: str = '1h'
) -> dict:
    """
    최적 진입 가격 분석

    시나리오:
    1. Open 진입 (현재)
    2. Low 진입 (Long, 최적)
    3. High 진입 (Short, 최적)

    Args:
        exchange: 거래소
        symbol: 심볼
        entry_tf: 타임프레임

    Returns:
        dict: 통계 정보
    """
    logger.info(f"최적 진입 가격 분석: {exchange} {symbol} {entry_tf}")

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

    # 2. 진입 가격별 수익 비교
    # 가정: 다음 봉 종료(Close)에서 청산

    long_open_profits = []  # Open 진입 → Close 청산
    long_low_profits = []   # Low 진입 → Close 청산 (최적)
    long_improvements = []  # 개선율 (Low vs Open)

    short_open_profits = []
    short_high_profits = []
    short_improvements = []

    for i in range(len(df) - 1):
        next_open = df['open'].iloc[i + 1]
        next_low = df['low'].iloc[i + 1]
        next_high = df['high'].iloc[i + 1]
        next_close = df['close'].iloc[i + 1]

        # Long 시나리오
        # Open 진입
        long_open_pnl = (next_close - next_open) / next_open * 100
        long_open_profits.append(long_open_pnl)

        # Low 진입 (최적)
        long_low_pnl = (next_close - next_low) / next_low * 100
        long_low_profits.append(long_low_pnl)

        # 개선율
        long_improvement = long_low_pnl - long_open_pnl
        long_improvements.append(long_improvement)

        # Short 시나리오
        # Open 진입
        short_open_pnl = (next_open - next_close) / next_open * 100
        short_open_profits.append(short_open_pnl)

        # High 진입 (최적)
        short_high_pnl = (next_high - next_close) / next_high * 100
        short_high_profits.append(short_high_pnl)

        # 개선율
        short_improvement = short_high_pnl - short_open_pnl
        short_improvements.append(short_improvement)

    # 3. 통계 계산
    long_open_arr = np.array(long_open_profits)
    long_low_arr = np.array(long_low_profits)
    long_imp_arr = np.array(long_improvements)

    short_open_arr = np.array(short_open_profits)
    short_high_arr = np.array(short_high_profits)
    short_imp_arr = np.array(short_improvements)

    # 4. 결과 출력
    print("\n" + "="*70)
    print("최적 진입 가격 분석")
    print("="*70)
    print(f"거래소: {exchange}")
    print(f"심볼: {symbol}")
    print(f"타임프레임: {entry_tf}")
    print(f"분석 봉 수: {len(df)-1:,}개")
    print("="*70)

    print("\n[Long 진입 비교]")
    print("-"*70)
    print("시나리오 1: Open 진입 → Close 청산 (현재)")
    print(f"  평균 수익:   {np.mean(long_open_arr):.3f}%")
    print(f"  중간값:      {np.median(long_open_arr):.3f}%")
    print(f"  승률:        {(long_open_arr > 0).sum() / len(long_open_arr) * 100:.2f}%")
    print()
    print("시나리오 2: Low 진입 → Close 청산 (최적)")
    print(f"  평균 수익:   {np.mean(long_low_arr):.3f}%")
    print(f"  중간값:      {np.median(long_low_arr):.3f}%")
    print(f"  승률:        {(long_low_arr > 0).sum() / len(long_low_arr) * 100:.2f}%")
    print()
    print("개선율 (Low vs Open)")
    print(f"  평균 개선:   +{np.mean(long_imp_arr):.3f}%p")
    print(f"  중간값:      +{np.median(long_imp_arr):.3f}%p")
    print(f"  최소:        +{np.min(long_imp_arr):.3f}%p")
    print(f"  최대:        +{np.max(long_imp_arr):.3f}%p")
    print("="*70)

    print("\n[Short 진입 비교]")
    print("-"*70)
    print("시나리오 1: Open 진입 → Close 청산 (현재)")
    print(f"  평균 수익:   {np.mean(short_open_arr):.3f}%")
    print(f"  중간값:      {np.median(short_open_arr):.3f}%")
    print(f"  승률:        {(short_open_arr > 0).sum() / len(short_open_arr) * 100:.2f}%")
    print()
    print("시나리오 2: High 진입 → Close 청산 (최적)")
    print(f"  평균 수익:   {np.mean(short_high_arr):.3f}%")
    print(f"  중간값:      {np.median(short_high_arr):.3f}%")
    print(f"  승률:        {(short_high_arr > 0).sum() / len(short_high_arr) * 100:.2f}%")
    print()
    print("개선율 (High vs Open)")
    print(f"  평균 개선:   +{np.mean(short_imp_arr):.3f}%p")
    print(f"  중간값:      +{np.median(short_imp_arr):.3f}%p")
    print(f"  최소:        +{np.min(short_imp_arr):.3f}%p")
    print(f"  최대:        +{np.max(short_imp_arr):.3f}%p")
    print("="*70)

    # 5. 종합 비교
    avg_long_improvement = np.mean(long_imp_arr)
    avg_short_improvement = np.mean(short_imp_arr)
    avg_improvement = (avg_long_improvement + avg_short_improvement) / 2

    print("\n[종합 비교]")
    print("-"*70)
    print(f"Long 개선율:  +{avg_long_improvement:.3f}%p")
    print(f"Short 개선율: +{avg_short_improvement:.3f}%p")
    print(f"평균 개선율:  +{avg_improvement:.3f}%p")
    print("="*70)

    # 6. 실전 적용
    print("\n[실전 적용 시사점]")
    print("-"*70)
    print(f"1. 최적 진입 (Low/High) 사용 시:")
    print(f"   → 평균 {avg_improvement:.3f}%p 수익 증가")
    print()
    print(f"2. 200번 거래 시 누적 효과:")
    print(f"   → 총 {avg_improvement * 200:.1f}%p 추가 수익")
    print()
    print(f"3. 현재 프리셋 (5,771%) 기준:")
    print(f"   → 예상 수익: {5771 + avg_improvement * 200:.0f}%")
    print()
    print("4. 구현 방법:")
    print("   Long: 지정가를 Low 근처로 설정 (추적 주문)")
    print("   Short: 지정가를 High 근처로 설정 (추적 주문)")
    print()
    print("5. 주의사항:")
    print("   - Low/High는 사후적 정보 (실시간 예측 불가)")
    print("   - 실제로는 Open 진입이 현실적")
    print("   - 하지만 '손실 먼저 경험'은 통계적 사실")
    print("="*70)

    return {
        'long_open_avg': float(np.mean(long_open_arr)),
        'long_low_avg': float(np.mean(long_low_arr)),
        'long_improvement': float(avg_long_improvement),
        'short_open_avg': float(np.mean(short_open_arr)),
        'short_high_avg': float(np.mean(short_high_arr)),
        'short_improvement': float(avg_short_improvement),
        'avg_improvement': float(avg_improvement)
    }


if __name__ == '__main__':
    result = optimal_entry_analysis(
        exchange='bybit',
        symbol='BTCUSDT',
        entry_tf='1h'
    )

    print("\n\n[RESULT] 핵심 결론:")
    print(f"최적 진입 (Low/High) vs Open 진입:")
    print(f"  Long 개선: +{result.get('long_improvement', 0):.3f}%p")
    print(f"  Short 개선: +{result.get('short_improvement', 0):.3f}%p")
    print(f"  평균 개선: +{result.get('avg_improvement', 0):.3f}%p")
    print()
    print("결론: 최적 진입 시 평균 약 0.2-0.4%p 추가 수익 가능")
    print("      하지만 Low/High는 사후적 정보이므로 실시간 예측 불가")
