#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v7.23 프리셋 빠른 검증

MACD vs ADX 프리셋 성능 비교 (15초)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.data_utils import resample_data
from utils.metrics import calculate_backtest_metrics


def quick_backtest(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    timeframe: str = '1h'
):
    """두 프리셋 빠른 비교"""

    print("="*70)
    print("v7.23 프리셋 빠른 검증")
    print("="*70)

    # 1. 데이터 로드
    print("\n[1/3] 데이터 로드 중...")
    dm = BotDataManager(exchange, symbol, {'entry_tf': '15m'})
    df_15m = dm.get_full_history(with_indicators=False)

    if df_15m is None:
        print("[ERROR] 데이터 로드 실패")
        return

    # timestamp 변환
    if pd.api.types.is_numeric_dtype(df_15m['timestamp']):
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
    else:
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])

    # 리샘플링
    df = resample_data(df_15m, timeframe, add_indicators=False)

    print(f"[OK] 데이터 로드 완료: {len(df):,}개 캔들")
    print(f"  기간: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

    # 2. MACD 프리셋 (v7.23)
    print(f"\n{'='*70}")
    print("MACD 프리셋 백테스트")
    print("="*70)

    macd_params = {
        'trend_interval': '1h',
        'atr_mult': 1.0,
        'filter_tf': '4h',
        'trail_start_r': 1.2,
        'trail_dist_r': 0.015,
        'entry_validity_hours': 6.0,
        'strategy_type': 'macd'
    }

    strategy_macd = AlphaX7Core(use_mtf=True, strategy_type='macd')
    trades_macd = strategy_macd.run_backtest(
        df_pattern=df,
        df_entry=df,
        **macd_params
    )

    # 메트릭 계산
    result_macd = calculate_backtest_metrics(trades_macd, leverage=1, capital=100.0)

    print(f"\n[2/3] MACD 결과:")
    print(f"  승률: {result_macd['win_rate']:.1f}%")
    print(f"  MDD: {result_macd['mdd']:.2f}%")
    print(f"  Sharpe: {result_macd['sharpe_ratio']:.2f}")
    print(f"  Profit Factor: {result_macd['profit_factor']:.2f}")
    print(f"  총 거래: {result_macd['total_trades']}회")

    # 3. ADX 프리셋 (v7.23)
    print(f"\n{'='*70}")
    print("ADX 프리셋 백테스트")
    print("="*70)

    adx_params = {
        'trend_interval': '1h',
        'atr_mult': 1.2,
        'filter_tf': '4h',
        'trail_start_r': 0.8,
        'trail_dist_r': 0.015,
        'entry_validity_hours': 72.0,
        'adx_period': 10.0,
        'adx_threshold': 20.0,
        'strategy_type': 'adx'
    }

    strategy_adx = AlphaX7Core(use_mtf=True, strategy_type='adx')
    trades_adx = strategy_adx.run_backtest(
        df_pattern=df,
        df_entry=df,
        **adx_params
    )

    # 메트릭 계산
    result_adx = calculate_backtest_metrics(trades_adx, leverage=1, capital=100.0)

    print(f"\n[3/3] ADX 결과:")
    print(f"  승률: {result_adx['win_rate']:.1f}%")
    print(f"  MDD: {result_adx['mdd']:.2f}%")
    print(f"  Sharpe: {result_adx['sharpe_ratio']:.2f}")
    print(f"  Profit Factor: {result_adx['profit_factor']:.2f}")
    print(f"  총 거래: {result_adx['total_trades']}회")

    # 4. 비교표
    print(f"\n{'='*70}")
    print("최종 비교")
    print("="*70)

    print(f"\n{'지표':<20} {'MACD':>15} {'ADX':>15} {'우위':>10}")
    print("-"*70)

    # 승률
    wr_diff = result_adx['win_rate'] - result_macd['win_rate']
    wr_winner = "ADX" if wr_diff > 0 else "MACD"
    print(f"{'승률':<20} {result_macd['win_rate']:>14.1f}% {result_adx['win_rate']:>14.1f}% {wr_winner:>10}")

    # MDD (낮을수록 좋음)
    mdd_diff = result_macd['mdd'] - result_adx['mdd']
    mdd_winner = "ADX" if mdd_diff > 0 else "MACD"
    print(f"{'MDD (낮을수록 좋음)':<20} {result_macd['mdd']:>14.2f}% {result_adx['mdd']:>14.2f}% {mdd_winner:>10}")

    # Sharpe
    sharpe_macd = result_macd['sharpe_ratio']
    sharpe_adx = result_adx['sharpe_ratio']
    sharpe_diff = sharpe_adx - sharpe_macd
    sharpe_winner = "ADX" if sharpe_diff > 0 else "MACD"
    print(f"{'Sharpe Ratio':<20} {sharpe_macd:>15.2f} {sharpe_adx:>15.2f} {sharpe_winner:>10}")

    # Profit Factor
    pf_macd = result_macd['profit_factor']
    pf_adx = result_adx['profit_factor']
    pf_diff = pf_adx - pf_macd
    pf_winner = "ADX" if pf_diff > 0 else "MACD"
    print(f"{'Profit Factor':<20} {pf_macd:>15.2f} {pf_adx:>15.2f} {pf_winner:>10}")

    # 거래 수
    trades_macd_count = result_macd['total_trades']
    trades_adx_count = result_adx['total_trades']
    trades_diff = trades_adx_count - trades_macd_count
    trades_winner = "ADX" if trades_diff > 0 else "MACD"
    print(f"{'총 거래':<20} {trades_macd_count:>15}회 {trades_adx_count:>15}회 {trades_winner:>10}")

    # 승자 집계
    print(f"\n{'='*70}")
    winners = {
        'MACD': sum([1 for w in [wr_winner, mdd_winner, sharpe_winner, pf_winner, trades_winner] if w == 'MACD']),
        'ADX': sum([1 for w in [wr_winner, mdd_winner, sharpe_winner, pf_winner, trades_winner] if w == 'ADX'])
    }

    if winners['ADX'] > winners['MACD']:
        print(f"[WINNER] ADX ({winners['ADX']}/5 지표)")
    elif winners['MACD'] > winners['ADX']:
        print(f"[WINNER] MACD ({winners['MACD']}/5 지표)")
    else:
        print(f"[TIE] 무승부 (각 {winners['ADX']}/5 지표)")

    print("="*70)


if __name__ == '__main__':
    quick_backtest()
