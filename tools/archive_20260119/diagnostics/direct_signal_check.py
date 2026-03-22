"""
직접 전략으로 신호 감지 및 OHLCV 확인 (v7.24)
작성일: 2026-01-18

목적:
- AlphaX7Core 직접 사용
- 신호 발생 시점 OHLCV 확인
- 지정가 체결 가능 여부 분석

실행:
python tools/direct_signal_check.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.indicators import add_all_indicators
from utils.data_utils import resample_ohlcv
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def direct_signal_check(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    entry_tf: str = '1h',
    max_signals: int = 10
) -> None:
    """
    직접 전략으로 신호 감지 및 OHLCV 확인

    Args:
        exchange: 거래소
        symbol: 심볼
        entry_tf: 타임프레임
        max_signals: 최대 표시 신호 수
    """
    logger.info(f"직접 신호 감지 시작: {exchange} {symbol} {entry_tf}")

    # 1. 데이터 로드
    dm = BotDataManager(exchange, symbol, {'entry_tf': entry_tf})
    dm.load_historical()

    if dm.df_entry_full is None:
        logger.error("데이터 부족")
        return

    df_15m = dm.df_entry_full.copy()

    if len(df_15m) < 200:
        logger.error("데이터 부족")
        return

    logger.info(f"15m 데이터: {len(df_15m):,}개 봉")

    # 2. 리샘플링 (1h)
    df_1h = resample_ohlcv(df_15m, '1h')
    logger.info(f"1h 데이터: {len(df_1h):,}개 봉")

    # 3. 지표 추가
    df_15m = add_all_indicators(df_15m, inplace=False)
    df_1h = add_all_indicators(df_1h, inplace=False)

    # 4. 전략 초기화
    strategy = AlphaX7Core()

    # 5. 신호 감지 (sliding window)
    signals = []
    logger.info("신호 감지 중...")

    for i in range(200, min(5000, len(df_1h) - 1)):  # 최대 5000개 봉만 검사 (속도 향상)
        df_1h_sub = df_1h.iloc[:i+1].copy()
        df_15m_sub = df_15m.iloc[:i*4+4].copy()  # 1h = 4 x 15m

        signal = strategy.detect_signal(
            df_1h=df_1h_sub,
            df_15m=df_15m_sub,
            filter_tf='4h',
            macd_fast=6,
            macd_slow=18,
            macd_signal=7,
            atr_period=14,
            entry_validity_hours=6.0
        )

        if signal and hasattr(signal, 'signal_type') and signal.signal_type in ['Long', 'Short']:
            # 신호 발생 시점 정보 저장
            signal_time = df_1h.index[i]
            entry_time = df_1h.index[i + 1]  # 다음 봉

            signals.append({
                'signal_idx': i,
                'entry_idx': i + 1,
                'signal_time': signal_time,
                'entry_time': entry_time,
                'side': signal.signal_type,
                'signal_price': df_1h.iloc[i]['close'],  # 신호 발생 시점 close
            })

            if len(signals) >= max_signals:
                break

    logger.info(f"신호 발견: {len(signals)}개")

    if len(signals) == 0:
        print("\n신호가 발견되지 않았습니다.")
        return

    # 6. 신호 정보 출력
    print("\n" + "="*100)
    print(f"실제 신호 OHLCV 분석 ({exchange} {symbol} {entry_tf})")
    print("="*100)
    print(f"총 신호 수: {len(signals)}개")
    print("="*100)

    for idx, sig in enumerate(signals):
        print(f"\n[신호 #{idx+1}]")
        print("-"*100)

        signal_idx = sig['signal_idx']
        entry_idx = sig['entry_idx']
        side = sig['side']

        # 신호 발생 봉
        signal_candle = df_1h.iloc[signal_idx]
        signal_time = sig['signal_time']

        # 진입 봉
        entry_candle = df_1h.iloc[entry_idx]
        entry_time = sig['entry_time']

        print(f"방향: {side}")
        print(f"신호 발생 시점: {signal_time}")
        print(f"진입 시점: {entry_time}")
        print()

        # 신호 발생 봉 OHLCV
        print(f"[신호 발생 봉] {signal_time}")
        print(f"  Open:   {signal_candle['open']:>10.2f}")
        print(f"  High:   {signal_candle['high']:>10.2f}")
        print(f"  Low:    {signal_candle['low']:>10.2f}")
        print(f"  Close:  {signal_candle['close']:>10.2f}  <- 신호 발생 (봉 종료)")
        print(f"  Volume: {signal_candle['volume']:>10,.0f}")
        print()

        # 진입 봉 OHLCV
        print(f"[진입 봉] {entry_time}")
        print(f"  Open:   {entry_candle['open']:>10.2f}  <- 진입 시도 가격")
        print(f"  High:   {entry_candle['high']:>10.2f}")
        print(f"  Low:    {entry_candle['low']:>10.2f}")
        print(f"  Close:  {entry_candle['close']:>10.2f}")
        print(f"  Volume: {entry_candle['volume']:>10,.0f}")
        print()

        # 지정가 체결 분석
        next_open = entry_candle['open']
        next_low = entry_candle['low']
        next_high = entry_candle['high']

        if side == 'Long':
            # Long: Open × 1.00042 지정가 (75% 체결률)
            limit_price = next_open * 1.00042
            filled = next_low <= limit_price
            gap = (next_low - limit_price) / limit_price * 100

            print(f"[지정가 분석 - Long]")
            print(f"  지정가 (75%):  {limit_price:>10.2f}  (Open x 1.00042)")
            print(f"  다음 봉 Low:   {next_low:>10.2f}")
            print(f"  체결 가능:     {'YES' if filled else 'NO':>10}")
            print(f"  갭:            {gap:>10.3f}%")
            print()

            # 보너스: 0.1% 프리미엄도 확인
            limit_price_01 = next_open * 1.001
            filled_01 = next_low <= limit_price_01
            gap_01 = (next_low - limit_price_01) / limit_price_01 * 100

            print(f"  [참고] 0.1% 지정가:")
            print(f"  지정가:        {limit_price_01:>10.2f}  (Open x 1.001)")
            print(f"  체결 가능:     {'YES' if filled_01 else 'NO':>10}")
            print(f"  갭:            {gap_01:>10.3f}%")

        elif side == 'Short':
            # Short: Open × 0.99753 지정가 (75% 체결률)
            limit_price = next_open * 0.99753
            filled = next_high >= limit_price
            gap = (limit_price - next_high) / limit_price * 100

            print(f"[지정가 분석 - Short]")
            print(f"  지정가 (75%):  {limit_price:>10.2f}  (Open x 0.99753)")
            print(f"  다음 봉 High:  {next_high:>10.2f}")
            print(f"  체결 가능:     {'YES' if filled else 'NO':>10}")
            print(f"  갭:            {gap:>10.3f}%")
            print()

            # 보너스: 0.1% 프리미엄도 확인
            limit_price_01 = next_open * 0.999
            filled_01 = next_high >= limit_price_01
            gap_01 = (limit_price_01 - next_high) / limit_price_01 * 100

            print(f"  [참고] 0.1% 지정가:")
            print(f"  지정가:        {limit_price_01:>10.2f}  (Open x 0.999)")
            print(f"  체결 가능:     {'YES' if filled_01 else 'NO':>10}")
            print(f"  갭:            {gap_01:>10.3f}%")

        print("-"*100)

    print("\n" + "="*100)


if __name__ == '__main__':
    direct_signal_check(
        exchange='bybit',
        symbol='BTCUSDT',
        entry_tf='1h',
        max_signals=10  # 최대 10개 신호 표시
    )
