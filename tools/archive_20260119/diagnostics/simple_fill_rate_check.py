"""
지정가 주문 체결률 초간단 확인 (v7.24)
작성일: 2026-01-18

목적:
- 백테스트 신호 없이, 순수하게 OHLC 데이터만으로 체결률 확인
- 가정: 매 봉마다 신호 발생
- 지정가 = 다음 봉 open × (1 + 0.001) (Long)
- 체결 조건: 다음 봉 Low < 지정가

실행:
python tools/simple_fill_rate_check.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from core.data_manager import BotDataManager
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def simple_fill_rate_check(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    entry_tf: str = '1h',
    limit_pct: float = 0.001  # 0.1%
) -> dict:
    """
    매 봉마다 신호 발생 가정 하에 지정가 체결률 확인

    Args:
        exchange: 거래소
        symbol: 심볼
        entry_tf: 타임프레임
        limit_pct: 지정가 프리미엄 (0.1% = 0.001)

    Returns:
        dict: {
            'total_candles': 전체 봉 수,
            'filled_count': 체결 가능 봉 수,
            'fill_rate': 체결률 (%),
            'failed_count': 미체결 봉 수
        }
    """
    logger.info(f"지정가 체결률 확인 시작: {exchange} {symbol} {entry_tf}")

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

    # 2. 체결 여부 확인 (매 봉마다 Long 신호 가정)
    filled_count = 0
    failed_count = 0
    failed_examples = []

    for i in range(len(df) - 1):  # 마지막 봉 제외 (다음 봉 없음)
        current_open = df['open'].iloc[i]
        next_open = df['open'].iloc[i + 1]
        next_low = df['low'].iloc[i + 1]
        next_high = df['high'].iloc[i + 1]

        # Long 지정가 주문 (다음 봉 open × 1.001)
        limit_price_long = next_open * (1 + limit_pct)
        filled_long = next_low <= limit_price_long

        # Short 지정가 주문 (다음 봉 open × 0.999)
        limit_price_short = next_open * (1 - limit_pct)
        filled_short = next_high >= limit_price_short

        # 평균 체결률 (Long + Short) / 2
        if filled_long:
            filled_count += 0.5
        else:
            failed_count += 0.5
            if len(failed_examples) < 3:
                failed_examples.append({
                    'timestamp': df.index[i],
                    'side': 'Long',
                    'limit_price': limit_price_long,
                    'next_low': next_low,
                    'gap_pct': (next_low - limit_price_long) / limit_price_long * 100
                })

        if filled_short:
            filled_count += 0.5
        else:
            failed_count += 0.5
            if len(failed_examples) < 3:
                failed_examples.append({
                    'timestamp': df.index[i],
                    'side': 'Short',
                    'limit_price': limit_price_short,
                    'next_high': next_high,
                    'gap_pct': (limit_price_short - next_high) / limit_price_short * 100
                })

    total_candles = len(df) - 1
    fill_rate = (filled_count / total_candles * 100) if total_candles > 0 else 0.0

    # 3. 결과 출력
    print("\n" + "="*70)
    print("지정가 주문 체결률 분석 (단순 OHLC 기반)")
    print("="*70)
    print(f"거래소: {exchange}")
    print(f"심볼: {symbol}")
    print(f"타임프레임: {entry_tf}")
    print(f"지정가 프리미엄: {limit_pct*100:.2f}%")
    print(f"데이터 기간: {df.index[0]} ~ {df.index[-1]}")
    print(f"총 봉 수: {len(df):,}개")
    print("-"*70)
    print(f"분석 봉 수: {total_candles:,}개 (마지막 봉 제외)")
    print(f"체결 가능: {filled_count:.0f}개 (Long + Short 평균)")
    print(f"미체결: {failed_count:.0f}개")
    print(f"체결률: {fill_rate:.2f}%")
    print("="*70)

    if failed_examples:
        print("\n미체결 사례 (최대 3개):")
        print("-"*70)
        for ex in failed_examples:
            print(f"시간: {ex['timestamp']}")
            print(f"방향: {ex['side']}")
            print(f"지정가: {ex['limit_price']:.2f}")
            if ex['side'] == 'Long':
                print(f"다음 봉 Low: {ex['next_low']:.2f}")
            else:
                print(f"다음 봉 High: {ex['next_high']:.2f}")
            print(f"갭: {ex['gap_pct']:.3f}%")
            print("-"*70)

    print("\n[NOTE] 해석:")
    print(f"- 모든 봉에서 신호 발생 가정 시 체결률: {fill_rate:.2f}%")
    print(f"- 실제 신호는 이보다 적으므로, 실제 체결률은 더 높을 수 있음")
    print(f"- {limit_pct*100:.2f}% 프리미엄 지정가 사용 시 예상 체결률")

    return {
        'total_candles': total_candles,
        'filled_count': int(filled_count),
        'fill_rate': fill_rate,
        'failed_count': int(failed_count),
        'failed_examples': failed_examples
    }


if __name__ == '__main__':
    # 기본 설정: Bybit BTC/USDT 1h
    result = simple_fill_rate_check(
        exchange='bybit',
        symbol='BTCUSDT',
        entry_tf='1h',
        limit_pct=0.001  # 0.1%
    )

    print("\n\n[RESULT] 최종 결론:")
    print(f"체결률: {result.get('fill_rate', 0):.2f}%")
    print(f"-> 지정가 주문 (open x 1.001) 사용 시 약 {result.get('fill_rate', 0):.0f}% 체결 예상")
