#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Walk-Forward 검증 스크립트

In-Sample (80%): 최적화
Out-of-Sample (20%): 검증

과적합 방지 필수 검증
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core
from utils.data_utils import resample_data


def walk_forward_validation(
    exchange: str = 'bybit',
    symbol: str = 'BTCUSDT',
    timeframe: str = '1h',
    strategy_type: str = 'macd',
    optimal_params: dict | None = None
):
    """
    Walk-Forward 검증

    Args:
        exchange: 거래소
        symbol: 심볼
        timeframe: 타임프레임
        strategy_type: 전략 타입
        optimal_params: 최적 파라미터
    """
    print("="*70)
    print("Walk-Forward 검증")
    print("="*70)

    # 1. 데이터 로드
    dm = BotDataManager(exchange, symbol, {'entry_tf': '15m'})
    df_15m = dm.get_full_history(with_indicators=False)

    if df_15m is None:
        print("❌ 데이터 로드 실패")
        return

    # timestamp 변환
    if pd.api.types.is_numeric_dtype(df_15m['timestamp']):
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
    else:
        df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'])

    # 리샘플링
    df = resample_data(df_15m, timeframe, add_indicators=False)

    # 2. In-Sample / Out-of-Sample 분할
    split_point = int(len(df) * 0.8)

    df_in_sample = df.iloc[:split_point].copy()
    df_out_sample = df.iloc[split_point:].copy()

    print(f"\n📊 데이터 분할")
    print(f"In-Sample (80%): {len(df_in_sample):,}개 ({df_in_sample['timestamp'].iloc[0]} ~ {df_in_sample['timestamp'].iloc[-1]})")
    print(f"Out-of-Sample (20%): {len(df_out_sample):,}개 ({df_out_sample['timestamp'].iloc[0]} ~ {df_out_sample['timestamp'].iloc[-1]})")

    # 3. 최적 파라미터가 없으면 기본값 사용
    if optimal_params is None:
        if strategy_type == 'macd':
            # v7.22 최적 파라미터
            optimal_params = {
                'trend_interval': timeframe,
                'atr_mult': 1.0,
                'filter_tf': '4h',
                'trail_start_r': 1.2,
                'trail_dist_r': 0.015,
                'entry_validity_hours': 6.0,
                'strategy_type': 'macd'
            }
        else:
            optimal_params = {
                'trend_interval': timeframe,
                'atr_mult': 1.2,
                'filter_tf': '4h',
                'trail_start_r': 0.8,
                'trail_dist_r': 0.015,
                'entry_validity_hours': 57.6,
                'adx_period': 10.0,
                'adx_threshold': 10.0,
                'strategy_type': 'adx'
            }

    # 4. In-Sample 백테스트
    print(f"\n{'─'*70}")
    print(f"In-Sample 백테스트 (최적화 구간)")
    print(f"{'─'*70}")

    strategy_in = AlphaX7Core(use_mtf=True, strategy_type=strategy_type)
    result_in = strategy_in.run_backtest(
        df_pattern=df_in_sample,
        df_entry=df_in_sample,
        **optimal_params
    )

    print(f"승률: {result_in['win_rate']:.1f}%")
    print(f"MDD: {result_in['max_drawdown']:.2f}%")
    print(f"Sharpe: {result_in.get('sharpe_ratio', 0):.2f}")
    print(f"PF: {result_in.get('profit_factor', 0):.2f}")
    print(f"거래: {result_in.get('total_trades', 0)}회")

    # 5. Out-of-Sample 백테스트
    print(f"\n{'─'*70}")
    print(f"Out-of-Sample 백테스트 (검증 구간)")
    print(f"{'─'*70}")

    strategy_out = AlphaX7Core(use_mtf=True, strategy_type=strategy_type)
    result_out = strategy_out.run_backtest(
        df_pattern=df_out_sample,
        df_entry=df_out_sample,
        **optimal_params
    )

    print(f"승률: {result_out['win_rate']:.1f}%")
    print(f"MDD: {result_out['max_drawdown']:.2f}%")
    print(f"Sharpe: {result_out.get('sharpe_ratio', 0):.2f}")
    print(f"PF: {result_out.get('profit_factor', 0):.2f}")
    print(f"거래: {result_out.get('total_trades', 0)}회")

    # 6. 성능 비교
    print(f"\n{'='*70}")
    print(f"성능 비교 (과적합 체크)")
    print(f"{'='*70}")

    metrics = ['win_rate', 'max_drawdown', 'sharpe_ratio', 'profit_factor']
    for metric in metrics:
        in_val = result_in.get(metric, 0)
        out_val = result_out.get(metric, 0)

        if in_val > 0:
            diff_pct = ((out_val - in_val) / in_val) * 100
            status = "✅" if abs(diff_pct) < 20 else "⚠️"
            print(f"{status} {metric}: In={in_val:.2f}, Out={out_val:.2f} ({diff_pct:+.1f}%)")
        else:
            print(f"❓ {metric}: In={in_val:.2f}, Out={out_val:.2f}")

    # 7. 과적합 판정
    print(f"\n{'='*70}")

    win_rate_diff = abs(result_out['win_rate'] - result_in['win_rate'])
    sharpe_diff_pct = abs((result_out.get('sharpe_ratio', 0) - result_in.get('sharpe_ratio', 0)) / max(result_in.get('sharpe_ratio', 1), 1)) * 100

    if win_rate_diff < 10 and sharpe_diff_pct < 20:
        print("✅ 과적합 없음 (Out-of-Sample 성능 유지)")
        print("✅ 실전 배포 가능")
    elif win_rate_diff < 20 and sharpe_diff_pct < 30:
        print("⚠️ 경미한 과적합 (Out-of-Sample 성능 저하)")
        print("⚠️ 파라미터 재조정 권장")
    else:
        print("❌ 심각한 과적합 (Out-of-Sample 성능 급락)")
        print("❌ 실전 배포 불가, 전략 재설계 필요")

    print("="*70)


if __name__ == '__main__':
    # MACD 전략 검증
    print("\n🔍 MACD 전략 검증")
    walk_forward_validation(strategy_type='macd')

    print("\n" + "="*70 + "\n")

    # ADX 전략 검증
    print("\n🔍 ADX 전략 검증")
    walk_forward_validation(strategy_type='adx')
