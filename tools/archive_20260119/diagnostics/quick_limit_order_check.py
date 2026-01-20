"""
지정가 주문 체결률 빠른 확인 스크립트 (v7.24)
작성일: 2026-01-18

목적:
- 신호 발생 후 다음 봉에서 지정가 주문 체결 가능 여부 확인
- 지정가 = 다음 봉 open × (1 + 0.001) (Long)
- 체결 조건: 다음 봉 Low < 지정가

실행:
python tools/quick_limit_order_check.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from config.parameters import DEFAULT_PARAMS
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def check_limit_order_fill_rate(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    entry_tf: str = '1h',
    limit_pct: float = 0.001  # 0.1%
) -> dict:
    """
    지정가 주문 체결률 확인

    Args:
        exchange: 거래소
        symbol: 심볼
        entry_tf: 진입 타임프레임
        limit_pct: 지정가 프리미엄 (0.1% = 0.001)

    Returns:
        dict: {
            'total_signals': 전체 신호 수,
            'filled_count': 체결 신호 수,
            'fill_rate': 체결률 (%),
            'failed_count': 미체결 신호 수
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

    if len(df) < 200:
        logger.error("데이터 부족")
        return {}

    logger.info(f"데이터: {len(df):,}개 봉")

    # 2. 지표 추가
    from utils.indicators import add_all_indicators
    df = add_all_indicators(df, inplace=False)

    # 3. 전략 파라미터
    params = DEFAULT_PARAMS.copy()
    params.update({
        'macd_fast': 6,
        'macd_slow': 18,
        'macd_signal': 7,
        'atr_mult': 1.5,
        'filter_tf': '4h',
        'trail_start_r': 1.2,
        'trail_dist_r': 0.03,
        'entry_validity_hours': 6.0
    })

    # 4. 전략 초기화
    strategy = AlphaX7Core()

    # 5. 신호 감지
    signals = []
    for i in range(200, len(df)):
        df_sub = df.iloc[:i+1].copy()
        signal = strategy.detect_signal(df_sub, params)  # type: ignore[arg-type]

        if signal and hasattr(signal, 'side') and hasattr(signal, 'entry_price'):
            side_val = getattr(signal, 'side', None)
            if side_val in ['Long', 'Short']:
                signals.append({
                    'index': i,
                    'timestamp': df.index[i],
                    'side': side_val,
                    'price': getattr(signal, 'entry_price', 0),
                    'next_open': df['open'].iloc[i+1] if i+1 < len(df) else None,
                    'next_high': df['high'].iloc[i+1] if i+1 < len(df) else None,
                    'next_low': df['low'].iloc[i+1] if i+1 < len(df) else None,
                    'next_close': df['close'].iloc[i+1] if i+1 < len(df) else None
                })

    total_signals = len(signals)
    logger.info(f"전체 신호: {total_signals}개")

    if total_signals == 0:
        return {
            'total_signals': 0,
            'filled_count': 0,
            'fill_rate': 0.0,
            'failed_count': 0
        }

    # 6. 체결 여부 확인
    filled_count = 0
    failed_count = 0
    failed_examples = []

    for sig in signals:
        if sig['next_open'] is None:
            # 마지막 신호 (다음 봉 없음)
            continue

        # 지정가 주문 가격
        if sig['side'] == 'Long':
            limit_price = sig['next_open'] * (1 + limit_pct)  # 0.1% 위
            filled = sig['next_low'] <= limit_price
        else:  # Short
            limit_price = sig['next_open'] * (1 - limit_pct)  # 0.1% 아래
            filled = sig['next_high'] >= limit_price

        if filled:
            filled_count += 1
        else:
            failed_count += 1
            if len(failed_examples) < 5:
                failed_examples.append({
                    'timestamp': sig['timestamp'],
                    'side': sig['side'],
                    'limit_price': limit_price,
                    'next_low': sig['next_low'],
                    'next_high': sig['next_high'],
                    'gap_pct': (
                        (sig['next_low'] - limit_price) / limit_price * 100
                        if sig['side'] == 'Long'
                        else (limit_price - sig['next_high']) / limit_price * 100
                    )
                })

    fill_rate = (filled_count / total_signals * 100) if total_signals > 0 else 0.0

    # 7. 결과 출력
    print("\n" + "="*70)
    print("지정가 주문 체결률 분석")
    print("="*70)
    print(f"거래소: {exchange}")
    print(f"심볼: {symbol}")
    print(f"타임프레임: {entry_tf}")
    print(f"지정가 프리미엄: {limit_pct*100:.2f}%")
    print(f"데이터 기간: {df.index[0]} ~ {df.index[-1]}")
    print(f"총 봉 수: {len(df):,}개")
    print("-"*70)
    print(f"전체 신호: {total_signals}개")
    print(f"체결 신호: {filled_count}개")
    print(f"미체결 신호: {failed_count}개")
    print(f"체결률: {fill_rate:.2f}%")
    print("="*70)

    if failed_examples:
        print("\n미체결 사례 (최대 5개):")
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

    return {
        'total_signals': total_signals,
        'filled_count': filled_count,
        'fill_rate': fill_rate,
        'failed_count': failed_count,
        'failed_examples': failed_examples
    }


if __name__ == '__main__':
    # 기본 설정: Bybit BTC/USDT 1h
    result = check_limit_order_fill_rate(
        exchange='bybit',
        symbol='BTCUSDT',
        entry_tf='1h',
        limit_pct=0.001  # 0.1%
    )

    print("\n\n결과 요약:")
    print(f"체결률: {result.get('fill_rate', 0):.2f}%")
    print(f"전체 신호 대비 체결 신호: {result.get('filled_count', 0)}/{result.get('total_signals', 0)}")
