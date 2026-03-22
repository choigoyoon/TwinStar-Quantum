"""Meta 최적화 결과 상세 분석 - 거래 로그 및 통계

이 스크립트는 Meta 최적화로 추출된 파라미터로 백테스트를 실행하고,
개별 거래의 상세 정보를 분석합니다.

분석 항목:
1. 백테스트 메트릭 (Sharpe, Win Rate, MDD, PF 등)
2. 거래 통계 (평균 PnL, 중앙값, 표준편차 등)
3. 거래 로그 (상위 30개)
4. PnL 분포 (백분위수)
5. 시간대별 거래 분포

Usage:
    python tools/debug_single_backtest.py

Author: Claude Sonnet 4.5
Date: 2026-01-17
"""

import sys
sys.path.insert(0, '.')

import json
import pandas as pd
import numpy as np
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.indicators import add_all_indicators
from utils.metrics import calculate_backtest_metrics


def analyze_trades(trades):
    """거래 통계 분석"""
    if not trades:
        return None

    df_trades = pd.DataFrame(trades)

    # PnL 계산 (이미 있을 수도 있음)
    if 'pnl' not in df_trades.columns:
        df_trades['pnl'] = df_trades.apply(
            lambda r: ((r['exit_price'] - r['entry_price']) / r['entry_price'] * 100)
            if r['side'] == 'Long' else
            ((r['entry_price'] - r['exit_price']) / r['entry_price'] * 100),
            axis=1
        )

    # 승/패 분리
    winning_trades = df_trades[df_trades['pnl'] > 0]
    losing_trades = df_trades[df_trades['pnl'] <= 0]

    stats = {
        'total_trades': len(df_trades),
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': len(winning_trades) / len(df_trades) * 100 if len(df_trades) > 0 else 0,

        # PnL 통계
        'avg_pnl': df_trades['pnl'].mean(),
        'median_pnl': df_trades['pnl'].median(),
        'std_pnl': df_trades['pnl'].std(),
        'max_profit': df_trades['pnl'].max(),
        'max_loss': df_trades['pnl'].min(),

        # 승리 거래 통계
        'avg_win': winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0,
        'max_win': winning_trades['pnl'].max() if len(winning_trades) > 0 else 0,

        # 손실 거래 통계
        'avg_loss': losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0,
        'max_loss_trade': losing_trades['pnl'].min() if len(losing_trades) > 0 else 0,

        # Profit Factor
        'total_profit': winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0,
        'total_loss': abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 0,
    }

    if stats['total_loss'] > 0:
        stats['profit_factor'] = stats['total_profit'] / stats['total_loss']
    else:
        stats['profit_factor'] = float('inf') if stats['total_profit'] > 0 else 0

    return stats


def print_trade_log(trades, n=30):
    """거래 로그 출력 (상위 N개)"""
    if not trades:
        print("거래 없음")
        return

    df = pd.DataFrame(trades)

    # PnL 계산
    if 'pnl' not in df.columns:
        df['pnl'] = df.apply(
            lambda r: ((r['exit_price'] - r['entry_price']) / r['entry_price'] * 100)
            if r['side'] == 'Long' else
            ((r['entry_price'] - r['exit_price']) / r['entry_price'] * 100),
            axis=1
        )

    # 타임스탬프 변환
    if 'entry_time' in df.columns:
        df['entry_time'] = pd.to_datetime(df['entry_time'])

    print("\n" + "="*100)
    print(f"거래 로그 (상위 {min(n, len(df))}개)")
    print("="*100)
    print(f"{'Timestamp':<20s} {'Side':<6s} {'Entry':>10s} {'Exit':>10s} {'PnL(%)':>8s} {'Pattern':<10s}")
    print("-"*100)

    for _, row in df.head(n).iterrows():
        timestamp_val = row.get('entry_time', 'N/A')
        timestamp = 'N/A'
        if isinstance(timestamp_val, pd.Timestamp):
            timestamp = timestamp_val.strftime('%Y-%m-%d %H:%M')
        elif isinstance(timestamp_val, str):
            timestamp = timestamp_val

        side = str(row.get('side', 'N/A'))
        entry = float(row.get('entry_price', 0))
        exit_price = float(row.get('exit_price', 0))
        pnl = float(row.get('pnl', 0))
        pattern = str(row.get('pattern', 'N/A'))

        pnl_str = f"{pnl:+.2f}%"
        print(f"{timestamp:<20s} {side:<6s} {entry:>10.2f} {exit_price:>10.2f} {pnl_str:>8s} {pattern:<10s}")

    if len(df) > n:
        print(f"... ({len(df) - n}개 거래 생략)")


def main():
    # Meta 결과 로드
    meta_file = 'presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_010105.json'

    print("="*100)
    print("Meta 최적화 결과 상세 분석")
    print("="*100)

    with open(meta_file, 'r') as f:
        meta = json.load(f)

    # 데이터 로드
    print("\n데이터 로드 중...")
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
    dm.load_historical()

    if dm.df_entry_full is None:
        print("데이터 로드 실패")
        return

    df = dm.df_entry_full.copy().set_index('timestamp')
    df = df.resample('1h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    df = df.reset_index()
    df = add_all_indicators(df, inplace=False)

    print(f"데이터: {len(df)}개 캔들 ({df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]})")

    # Quick 파라미터 (시작값 - 최적 파라미터)
    p = meta['param_ranges_by_mode']
    params = {
        'atr_mult': p['atr_mult']['quick'][0],
        'filter_tf': p['filter_tf']['quick'][0],
        'trail_start_r': p['trail_start_r']['quick'][0],
        'trail_dist_r': p['trail_dist_r']['quick'][0],
        'entry_validity_hours': p['entry_validity_hours']['quick'][0]
    }

    print("\n최적 파라미터:")
    for k, v in params.items():
        print(f"  {k:22s}: {v}")

    # 백테스트 실행
    print("\n백테스트 실행 중...")
    strategy = AlphaX7Core(use_mtf=True)
    trades = strategy.run_backtest(
        df_pattern=df,
        df_entry=df,
        slippage=0.0005,
        pattern_tolerance=0.05,
        enable_pullback=False,
        **params
    )

    if not trades:
        print("\n거래 없음 - 파라미터 확인 필요")
        return

    # 거래 통계 분석
    stats = analyze_trades(trades)

    if stats is None:
        print("\n거래 통계 분석 실패")
        return

    # 메트릭 계산
    metrics = calculate_backtest_metrics(trades, leverage=1, capital=100.0)

    # 결과 출력
    print("\n" + "="*100)
    print("백테스트 메트릭")
    print("="*100)
    print(f"Sharpe Ratio      : {metrics['sharpe_ratio']:10.2f}")
    print(f"Win Rate          : {metrics['win_rate']:9.1f}%")
    print(f"MDD               : {metrics['mdd']:9.2f}%")
    print(f"Profit Factor     : {metrics['profit_factor']:10.2f}")
    print(f"Total Trades      : {metrics['total_trades']:10d}")
    print(f"Total PnL         : {metrics['total_pnl']:9.2f}%")

    # 거래 통계
    print("\n" + "="*100)
    print("거래 통계")
    print("="*100)
    print(f"총 거래           : {stats['total_trades']:10d}개")
    print(f"승리 거래         : {stats['winning_trades']:10d}개 ({stats['win_rate']:.1f}%)")
    print(f"손실 거래         : {stats['losing_trades']:10d}개")
    print()
    print(f"평균 PnL          : {stats['avg_pnl']:+10.3f}%")
    print(f"중앙값 PnL        : {stats['median_pnl']:+10.3f}%")
    print(f"표준편차          : {stats['std_pnl']:10.3f}%")
    print()
    print(f"최대 수익         : {stats['max_profit']:+10.3f}%")
    print(f"최대 손실         : {stats['max_loss']:+10.3f}%")
    print()
    print(f"평균 승리         : {stats['avg_win']:+10.3f}%")
    print(f"평균 손실         : {stats['avg_loss']:+10.3f}%")
    print()
    print(f"총 수익           : {stats['total_profit']:+10.2f}%")
    print(f"총 손실           : {stats['total_loss']:10.2f}%")
    print(f"Profit Factor     : {stats['profit_factor']:10.2f}")

    # 거래 로그
    print_trade_log(trades, n=30)

    # PnL 분포 분석
    print("\n" + "="*100)
    print("PnL 분포 (백분위수)")
    print("="*100)

    df_trades = pd.DataFrame(trades)
    if 'pnl' not in df_trades.columns:
        df_trades['pnl'] = df_trades.apply(
            lambda r: ((r['exit_price'] - r['entry_price']) / r['entry_price'] * 100)
            if r['side'] == 'Long' else
            ((r['entry_price'] - r['exit_price']) / r['entry_price'] * 100),
            axis=1
        )

    percentiles = [0, 5, 10, 25, 50, 75, 90, 95, 100]
    for p_val in percentiles:
        value = np.percentile(df_trades['pnl'], p_val)
        print(f"  {p_val:3d}%: {value:+8.3f}%")

    # 시간대별 분석
    if 'entry_time' in df_trades.columns:
        df_trades['entry_time'] = pd.to_datetime(df_trades['entry_time'])
        df_trades['hour'] = df_trades['entry_time'].dt.hour
        df_trades['weekday'] = df_trades['entry_time'].dt.dayofweek

        print("\n" + "="*100)
        print("시간대별 거래 분포")
        print("="*100)

        hourly_counts = df_trades.groupby('hour').size()
        print("\n시간별 거래수 (상위 10개):")
        top_hours = hourly_counts.sort_values(ascending=False).head(10)
        for hour_val in top_hours.index:
            hour_int = int(hour_val) if isinstance(hour_val, (int, float, np.integer, np.floating)) else 0
            count_val = int(top_hours[hour_val])
            print(f"  {hour_int:2d}시: {count_val:4d}개 ({count_val/len(df_trades)*100:5.1f}%)")

        print("\n요일별 거래수:")
        weekdays = ['월', '화', '수', '목', '금', '토', '일']
        weekday_counts = df_trades.groupby('weekday').size()
        for day_val in weekday_counts.index:
            day_int = int(day_val) if isinstance(day_val, (int, float, np.integer, np.floating)) else 0
            count_val = int(weekday_counts[day_val])
            # 인덱스 범위 체크
            if 0 <= day_int < len(weekdays):
                day_name = weekdays[day_int]
            else:
                day_name = f"Day{day_int}"
            print(f"  {day_name}: {count_val:4d}개 ({count_val/len(df_trades)*100:5.1f}%)")

    print("\n" + "="*100)
    print("분석 완료")
    print("="*100)


if __name__ == '__main__':
    main()
