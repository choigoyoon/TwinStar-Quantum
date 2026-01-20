"""
실제 신호 발생 시점 OHLCV 확인 (v7.24)
작성일: 2026-01-18

목적:
- 백테스트 신호 발생 시점의 OHLCV 확인
- 다음 봉 OHLCV와 비교
- 지정가 체결 가능 여부 확인

실행:
python tools/check_signal_ohlcv.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from core.data_manager import BotDataManager
from config.parameters import DEFAULT_PARAMS
from utils.logger import get_module_logger

# 백테스트 엔진 import (conditional import for type checking)
try:
    from trading.backtest.backtest_engine import BacktestEngine  # type: ignore
except ImportError:
    BacktestEngine = None  # type: ignore[assignment]

logger = get_module_logger(__name__)


def check_signal_ohlcv(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    entry_tf: str = '1h',
    max_signals: int = 20
) -> None:
    """
    실제 신호 발생 시점의 OHLCV 확인

    Args:
        exchange: 거래소
        symbol: 심볼
        entry_tf: 타임프레임
        max_signals: 최대 표시 신호 수
    """
    logger.info(f"신호 OHLCV 확인 시작: {exchange} {symbol} {entry_tf}")

    # 1. 데이터 로드
    dm = BotDataManager(exchange, symbol, {'entry_tf': entry_tf})
    dm.load_historical()

    if dm.df_entry_full is None:
        logger.error("데이터 부족")
        return

    df = dm.df_entry_full.copy()

    if len(df) < 200:
        logger.error("데이터 부족")
        return

    logger.info(f"데이터: {len(df):,}개 봉")

    # 2. 백테스트 파라미터
    params = DEFAULT_PARAMS.copy()
    params.update({
        'macd_fast': 6,
        'macd_slow': 18,
        'macd_signal': 7,
        'atr_mult': 1.5,
        'filter_tf': '4h',
        'trail_start_r': 1.2,
        'trail_dist_r': 0.03,
        'entry_validity_hours': 6.0,
        'leverage': 1
    })

    # 3. 백테스트 실행
    if BacktestEngine is None:
        logger.error("BacktestEngine을 import할 수 없습니다.")
        return

    logger.info("백테스트 실행 중...")
    engine = BacktestEngine(  # type: ignore[misc]
        df=df,
        params=params,
        strategy_type='macd',
        trend_tf=entry_tf
    )

    trades = engine.run()
    logger.info(f"신호 발견: {len(trades)}개")

    if len(trades) == 0:
        print("\n신호가 발견되지 않았습니다.")
        return

    # 4. 신호 정보 출력
    print("\n" + "="*100)
    print(f"실제 신호 OHLCV 분석 ({exchange} {symbol} {entry_tf})")
    print("="*100)
    print(f"총 신호 수: {len(trades)}개")
    print(f"표시 신호 수: {min(max_signals, len(trades))}개")
    print("="*100)

    for i, trade in enumerate(trades[:max_signals]):
        print(f"\n[신호 #{i+1}]")
        print("-"*100)

        # 신호 정보
        entry_time = trade.get('entry_time')
        side = trade.get('side', 'Unknown')
        entry_price = trade.get('entry_price', 0)
        exit_price = trade.get('exit_price', 0)
        pnl = trade.get('pnl', 0)

        # 진입 시점 인덱스 찾기
        if entry_time is None:
            continue

        try:
            entry_idx_raw = df.index.get_loc(entry_time)
            # get_loc은 int, slice, 또는 ndarray를 반환할 수 있음
            if isinstance(entry_idx_raw, int):
                entry_idx = entry_idx_raw
            else:
                continue
        except KeyError:
            continue

        # 신호 발생 시점 (entry_time - 1봉)
        signal_idx = entry_idx - 1
        if signal_idx < 0 or signal_idx >= len(df):
            continue

        # 신호 발생 봉
        signal_candle = df.iloc[signal_idx]
        signal_time = df.index[signal_idx]

        # 진입 봉 (다음 봉)
        entry_candle = df.iloc[entry_idx]

        print(f"방향: {side}")
        print(f"신호 발생 시점: {signal_time}")
        print(f"진입 시점: {entry_time}")
        print()

        # 신호 발생 봉 OHLCV
        print(f"[신호 발생 봉] {signal_time}")
        print(f"  Open:   {signal_candle['open']:.2f}")
        print(f"  High:   {signal_candle['high']:.2f}")
        print(f"  Low:    {signal_candle['low']:.2f}")
        print(f"  Close:  {signal_candle['close']:.2f}")
        print(f"  Volume: {signal_candle['volume']:,.0f}")
        print()

        # 진입 봉 (다음 봉) OHLCV
        print(f"[진입 봉] {entry_time}")
        print(f"  Open:   {entry_candle['open']:.2f}  <- 백테스트 진입가")
        print(f"  High:   {entry_candle['high']:.2f}")
        print(f"  Low:    {entry_candle['low']:.2f}")
        print(f"  Close:  {entry_candle['close']:.2f}")
        print(f"  Volume: {entry_candle['volume']:,.0f}")
        print()

        # 지정가 체결 가능 여부 확인
        next_open = entry_candle['open']
        next_low = entry_candle['low']
        next_high = entry_candle['high']

        if side == 'Long':
            # Long: Open × 1.00042 지정가
            limit_price = float(next_open * 1.00042)
            filled = bool(float(next_low) <= limit_price)
            gap = (float(next_low) - limit_price) / limit_price * 100

            print(f"[지정가 분석 - Long]")
            print(f"  지정가:        {limit_price:.2f}  (Open x 1.00042)")
            print(f"  다음 봉 Low:   {next_low:.2f}")
            print(f"  체결 가능:     {'YES' if filled else 'NO'}")
            print(f"  갭:            {gap:.3f}%")

        elif side == 'Short':
            # Short: Open × 0.99753 지정가
            limit_price = float(next_open * 0.99753)
            filled = bool(float(next_high) >= limit_price)
            gap = (limit_price - float(next_high)) / limit_price * 100

            print(f"[지정가 분석 - Short]")
            print(f"  지정가:        {limit_price:.2f}  (Open x 0.99753)")
            print(f"  다음 봉 High:  {next_high:.2f}")
            print(f"  체결 가능:     {'YES' if filled else 'NO'}")
            print(f"  갭:            {gap:.3f}%")

        print()

        # 백테스트 결과
        print(f"[백테스트 결과]")
        print(f"  진입가:   {entry_price:.2f}")
        print(f"  청산가:   {exit_price:.2f}")
        print(f"  PnL:      {pnl:+.2f}%")

        print("-"*100)

    print("\n" + "="*100)


if __name__ == '__main__':
    check_signal_ohlcv(
        exchange='bybit',
        symbol='BTCUSDT',
        entry_tf='1h',
        max_signals=20  # 최대 20개 신호 표시
    )
