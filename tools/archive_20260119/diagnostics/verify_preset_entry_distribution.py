"""
프리셋 검증 + 진입 캔들 O-H-L 분포 분석

Fine-Tuning Quick 최적 파라미터:
- atr_mult: 1.25
- filter_tf: 4h
- trail_start_r: 0.4
- trail_dist_r: 0.05

분석 항목:
1. 백테스트 메트릭 (승률, 거래수, 단리, 복리, MDD, 1회 평균 PNL)
2. 진입 캔들 분포:
   - Long: (O - L) / O × 100 분포
   - Short: (H - O) / O × 100 분포
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.strategy_core import AlphaX7Core
from core.data_manager import BotDataManager
from utils.metrics import calculate_backtest_metrics


def main():
    print("=" * 80)
    print("프리셋 검증 + 진입 캔들 O-H-L 분포 분석")
    print("=" * 80)

    # 최적 파라미터
    params = {
        'atr_mult': 1.25,
        'filter_tf': '4h',
        'trail_start_r': 0.4,
        'trail_dist_r': 0.05,
        'pattern_tolerance': 0.05,
        'entry_validity_hours': 6.0,
        'macd_fast': 6,
        'macd_slow': 18,
        'macd_signal': 7,
        'ema_period': 20,
        'rsi_period': 14,
        'atr_period': 14,
    }

    print("\n[1] 데이터 로드 중...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
    dm.load_historical()

    df_entry = dm.df_entry_full
    df_pattern = dm.df_pattern_full

    if df_entry is None or df_pattern is None:
        print("데이터 로드 실패")
        return

    if len(df_entry) < 100:
        print("데이터 부족")
        return

    print(f"OK Entry 데이터: {len(df_entry):,}개 (15m)")
    print(f"OK Pattern 데이터: {len(df_pattern):,}개 (1h)")

    # 백테스트 실행
    print("\n[2] 백테스트 실행 중...")
    strategy = AlphaX7Core(use_mtf=True, strategy_type='macd')

    result = strategy.run_backtest(
        df_pattern=df_pattern,
        df_entry=df_entry,
        slippage=0.0,
        collect_audit=True,  # 진입 캔들 수집
        allowed_direction='Both',  # Long + Short 모두 허용
        **params
    )

    # run_backtest 반환값 처리 (dict 또는 tuple)
    if isinstance(result, dict):
        trades = result.get('trades', [])
    elif isinstance(result, tuple):
        # tuple 반환 시: (trades,)
        trades = result[0] if len(result) > 0 else []
    else:
        trades = []

    if not trades:
        print("거래 없음")
        return

    print(f"OK 총 거래: {len(trades):,}회")

    # 거래 방향 확인 (디버깅)
    if trades:
        first_trade_keys = list(trades[0].keys())
        print(f"  첫 거래 키: {first_trade_keys[:10]}")  # 처음 10개만
        direction_field = trades[0].get('direction', trades[0].get('side', '없음'))
        print(f"  방향 필드 값: {direction_field}")

    # type, direction, side 필드 모두 확인
    long_count = sum(1 for t in trades if t.get('type') == 'Long' or t.get('direction') == 'Long' or t.get('side') == 'Long')
    short_count = sum(1 for t in trades if t.get('type') == 'Short' or t.get('direction') == 'Short' or t.get('side') == 'Short')
    print(f"  - Long: {long_count:,}회")
    print(f"  - Short: {short_count:,}회")

    # 메트릭 계산
    print("\n[3] 메트릭 계산 중...")
    metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    # 결과 출력
    print("\n" + "=" * 80)
    print("[백테스트 결과]")
    print("=" * 80)
    print(f"승률:         {metrics['win_rate']:.2f}%")
    print(f"총 거래:      {metrics['total_trades']:,}회")
    print(f"단리 수익:    {metrics['total_pnl']:.2f}%")
    print(f"복리 수익:    {metrics['compound_return']:.2f}%")
    print(f"MDD:          {metrics['mdd']:.2f}%")
    print(f"1회 평균 PNL: {metrics['avg_pnl']:.2f}%")
    print(f"Sharpe:       {metrics['sharpe_ratio']:.2f}")
    print(f"PF:           {metrics['profit_factor']:.2f}")

    # 진입 캔들 분포 분석
    print("\n[4] 진입 캔들 O-H-L 분포 분석 중...")

    # 거래 데이터에서 진입 시각 추출
    entry_times = []
    entry_sides = []
    entry_prices = []
    for t in trades:
        if 'entry_time' in t:
            entry_times.append(pd.to_datetime(t['entry_time'], unit='ms', utc=True))
            entry_sides.append(t.get('type', t.get('side', 'Long')))  # 'type' 우선, fallback 'side'
            entry_prices.append(t.get('entry', 0))  # 'entry_price' → 'entry'

    if not entry_times:
        print("진입 시각 정보 없음")
        return

    print(f"총 {len(entry_times):,}개 거래의 진입 캔들 분석 중...")

    # df_entry에서 진입 캔들 추출
    df_entry_copy = df_entry.copy()

    # timestamp 컬럼이 이미 datetime 타입인 경우 처리
    if df_entry_copy['timestamp'].dtype != 'datetime64[ns, UTC]':
        df_entry_copy['timestamp'] = pd.to_datetime(df_entry_copy['timestamp'], unit='ms', utc=True)

    entry_candles = []

    for entry_time, side, entry_price in zip(entry_times, entry_sides, entry_prices):
        # 진입 시각과 가장 가까운 캔들 찾기 (신호 발생 후 다음 캔들)
        # entry_time이 Timestamp인 경우 UTC로 변환
        if not hasattr(entry_time, 'tz') or entry_time.tz is None:
            entry_time = entry_time.tz_localize('UTC')

        future_candles = df_entry_copy[df_entry_copy['timestamp'] >= entry_time]
        if len(future_candles) == 0:
            continue

        candle = future_candles.iloc[0]  # 다음 캔들 (실제 진입 캔들)

        open_price = candle['open']
        high_price = candle['high']
        low_price = candle['low']
        close_price = candle['close']

        if side == 'Long':
            ol_diff = (open_price - low_price) / open_price * 100
            oc_diff = (close_price - open_price) / open_price * 100
        else:  # Short
            ho_diff = (high_price - open_price) / open_price * 100
            oc_diff = (open_price - close_price) / open_price * 100

        entry_candles.append({
            'side': side,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'ol_diff': ol_diff if side == 'Long' else None,
            'ho_diff': ho_diff if side == 'Short' else None,
            'oc_diff': oc_diff,
        })

    # 분포 분석
    long_candles = [c for c in entry_candles if c['side'] == 'Long']
    short_candles = [c for c in entry_candles if c['side'] == 'Short']

    print("\n" + "=" * 80)
    print("[진입 캔들 O-H-L 분포]")
    print("=" * 80)

    if long_candles:
        ol_diffs = [c['ol_diff'] for c in long_candles if c['ol_diff'] is not None]
        if ol_diffs:
            print(f"\n[Long] (O - L) / O × 100 분포 ({len(ol_diffs):,}개)")
            print(f"  평균:     {np.mean(ol_diffs):+.3f}%")
            print(f"  중간값:   {np.median(ol_diffs):+.3f}%")
            print(f"  표준편차: {np.std(ol_diffs):.3f}%")
            print(f"  최소:     {np.min(ol_diffs):+.3f}%")
            print(f"  최대:     {np.max(ol_diffs):+.3f}%")
            print(f"  25%:      {np.percentile(ol_diffs, 25):+.3f}%")
            print(f"  75%:      {np.percentile(ol_diffs, 75):+.3f}%")

            # 지정가 주문 권장 가격
            mean_ol = np.mean(ol_diffs)
            std_ol = np.std(ol_diffs)
            limit_price_offset = mean_ol - std_ol
            print(f"\n  지정가 주문 권장: next_open - {abs(limit_price_offset):.3f}%")
            print(f"     (평균 - 표준편차 = {mean_ol:.3f}% - {std_ol:.3f}%)")
    else:
        print("\n[Long] 데이터 없음")

    if short_candles:
        ho_diffs = [c['ho_diff'] for c in short_candles if c['ho_diff'] is not None]
        if ho_diffs:
            print(f"\n[Short] (H - O) / O × 100 분포 ({len(ho_diffs):,}개)")
            print(f"  평균:     {np.mean(ho_diffs):+.3f}%")
            print(f"  중간값:   {np.median(ho_diffs):+.3f}%")
            print(f"  표준편차: {np.std(ho_diffs):.3f}%")
            print(f"  최소:     {np.min(ho_diffs):+.3f}%")
            print(f"  최대:     {np.max(ho_diffs):+.3f}%")
            print(f"  25%:      {np.percentile(ho_diffs, 25):+.3f}%")
            print(f"  75%:      {np.percentile(ho_diffs, 75):+.3f}%")

            # 지정가 주문 권장 가격
            mean_ho = np.mean(ho_diffs)
            std_ho = np.std(ho_diffs)
            limit_price_offset = mean_ho - std_ho
            print(f"\n  지정가 주문 권장: next_open + {abs(limit_price_offset):.3f}%")
            print(f"     (평균 - 표준편차 = {mean_ho:.3f}% - {std_ho:.3f}%)")
    else:
        print("\n[Short] 데이터 없음")

    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
