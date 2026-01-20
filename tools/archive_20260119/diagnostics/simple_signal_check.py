"""
실제 신호 발생 시점 OHLCV 확인 (간단 버전, v7.24)
작성일: 2026-01-18

목적:
- core/optimizer.py 백테스트로 신호 추출
- 신호 발생 시점 OHLCV 확인
- 지정가 체결 가능 여부 확인

실행:
python tools/simple_signal_check.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer
from core.strategy_core import AlphaX7Core
from config.parameters import DEFAULT_PARAMS
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


def simple_signal_check(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    entry_tf: str = '1h',
    max_signals: int = 10
) -> None:
    """
    실제 신호 발생 시점의 OHLCV 확인 (간단 버전)

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

    # 2. 백테스트 파라미터 (MACD 프리셋)
    params = {
        'macd_fast': 6,
        'macd_slow': 18,
        'macd_signal': 7,
        'atr_mult': 1.5,
        'filter_tf': '4h',
        'trail_start_r': 1.2,
        'trail_dist_r': 0.03,
        'entry_validity_hours': 6.0,
        'leverage': 1
    }

    # 3. Optimizer로 백테스트
    logger.info("백테스트 실행 중...")
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type='macd'
    )

    result = optimizer._run_single(params, slippage=0.001, fee=0.00055)

    if result is None:
        print("\n백테스트 실패")
        return

    # trades는 list 또는 int (total_trades)
    if hasattr(result, 'trades') and isinstance(result.trades, list):
        trades = result.trades
    else:
        trades = []

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

        # 거래 정보
        entry_time = trade.get('entry_time')
        side = trade.get('side', 'Unknown')
        entry_price = trade.get('entry_price', 0)
        exit_price = trade.get('exit_price', 0)
        pnl = trade.get('pnl', 0)

        if entry_time is None:
            continue

        # Timestamp 변환
        if isinstance(entry_time, (int, float)):
            entry_time_ts = pd.Timestamp(entry_time, unit='ms', tz='UTC')
        else:
            entry_time_ts = pd.Timestamp(entry_time)

        # 진입 시점 인덱스 찾기
        try:
            # pd.Index 타입 변환
            entry_idx_arr = df.index.get_indexer(pd.Index([entry_time_ts]), method='nearest')
            if len(entry_idx_arr) > 0:
                entry_idx = int(entry_idx_arr[0])
            else:
                continue
        except Exception:
            continue

        if entry_idx < 1 or entry_idx >= len(df):
            continue

        # 신호 발생 봉 (진입 전 봉)
        signal_idx = entry_idx - 1
        signal_candle = df.iloc[signal_idx]
        signal_time = df.index[signal_idx]

        # 진입 봉
        entry_candle = df.iloc[entry_idx]
        entry_time_actual = df.index[entry_idx]

        print(f"방향: {side}")
        print(f"신호 발생 시점: {signal_time}")
        print(f"진입 시점: {entry_time_actual}")
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
        print(f"[진입 봉] {entry_time_actual}")
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
            print(f"  체결 가능:     {'YES ✓' if filled else 'NO ✗':>10}")
            print(f"  갭:            {gap:>10.3f}%")
            print()

            # 보너스: 0.1% 프리미엄도 확인
            limit_price_01 = next_open * 1.001
            filled_01 = next_low <= limit_price_01
            gap_01 = (next_low - limit_price_01) / limit_price_01 * 100

            print(f"  [참고] 0.1% 지정가:")
            print(f"  지정가:        {limit_price_01:>10.2f}  (Open x 1.001)")
            print(f"  체결 가능:     {'YES ✓' if filled_01 else 'NO ✗':>10}")
            print(f"  갭:            {gap_01:>10.3f}%")

        elif side == 'Short':
            # Short: Open × 0.99753 지정가 (75% 체결률)
            limit_price = next_open * 0.99753
            filled = next_high >= limit_price
            gap = (limit_price - next_high) / limit_price * 100

            print(f"[지정가 분석 - Short]")
            print(f"  지정가 (75%):  {limit_price:>10.2f}  (Open x 0.99753)")
            print(f"  다음 봉 High:  {next_high:>10.2f}")
            print(f"  체결 가능:     {'YES ✓' if filled else 'NO ✗':>10}")
            print(f"  갭:            {gap:>10.3f}%")
            print()

            # 보너스: 0.1% 프리미엄도 확인
            limit_price_01 = next_open * 0.999
            filled_01 = next_high >= limit_price_01
            gap_01 = (limit_price_01 - next_high) / limit_price_01 * 100

            print(f"  [참고] 0.1% 지정가:")
            print(f"  지정가:        {limit_price_01:>10.2f}  (Open x 0.999)")
            print(f"  체결 가능:     {'YES ✓' if filled_01 else 'NO ✗':>10}")
            print(f"  갭:            {gap_01:>10.3f}%")

        print()

        # 백테스트 결과
        print(f"[백테스트 결과]")
        print(f"  진입가:   {entry_price:>10.2f}")
        print(f"  청산가:   {exit_price:>10.2f}")
        print(f"  PnL:      {pnl:>10.2f}%")

        print("-"*100)

    print("\n" + "="*100)


if __name__ == '__main__':
    simple_signal_check(
        exchange='bybit',
        symbol='BTCUSDT',
        entry_tf='1h',
        max_signals=10  # 최대 10개 신호 표시
    )
