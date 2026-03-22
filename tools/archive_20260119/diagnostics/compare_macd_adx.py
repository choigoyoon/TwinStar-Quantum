#!/usr/bin/env python3
"""
MACD vs ADX Coarse-to-Fine Comparison Script
인코딩 이슈 해결 버전
"""

import sys
from pathlib import Path
import time

# Root 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer
from core.strategy_core import AlphaX7Core


def load_data(exchange='bybit', symbol='BTCUSDT', target_tf='1h'):
    """데이터 로드 및 리샘플링"""
    print("="*70)
    print("Data Loading")
    print("="*70)

    dm = BotDataManager(exchange, symbol, {'entry_tf': '15m'})
    df_15m = dm.get_full_history(with_indicators=False)

    if df_15m is None or df_15m.empty:
        print("ERROR: No data")
        return None

    print(f"15m data loaded: {len(df_15m):,} candles")

    # Resample
    if target_tf != '15m':
        from utils.data_utils import resample_data
        df = resample_data(df_15m, target_tf, add_indicators=False)
        print(f"Resampled to {target_tf}: {len(df):,} candles")
        return df

    return df_15m


def test_strategy(df, strategy_type='macd'):
    """단일 전략 테스트"""
    print("\n" + "="*70)
    print(f"Testing {strategy_type.upper()} Strategy")
    print("="*70)

    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type=strategy_type
    )

    # Phase 1: Coarse Grid
    print("\n--- Phase 1: Coarse Grid ---")
    start_time = time.time()
    coarse_results = optimizer.run_coarse_grid_optimization(
        df=df,
        trend_tf='1h',
        metric='sharpe_ratio'
    )
    coarse_time = time.time() - start_time

    if not coarse_results:
        print("ERROR: Coarse Grid failed")
        return None

    print(f"Coarse Grid: {len(coarse_results)} results in {coarse_time:.1f}s")
    print(f"Top Score: {coarse_results[0].sharpe_ratio:.2f}")
    print(f"Top Params: {coarse_results[0].params}")

    # Phase 2: Fine Grid
    print("\n--- Phase 2: Fine Grid ---")
    start_time = time.time()
    fine_results = optimizer.run_fine_grid_optimization(
        df=df,
        trend_tf='1h',
        coarse_results=coarse_results,
        top_n=20,
        metric='sharpe_ratio'
    )
    fine_time = time.time() - start_time

    if not fine_results:
        print("ERROR: Fine Grid failed")
        return None

    print(f"Fine Grid: {len(fine_results)} results in {fine_time:.1f}s")
    print(f"Top Score: {fine_results[0].sharpe_ratio:.2f}")
    print(f"Top Params: {fine_results[0].params}")

    # 결과 요약
    best = fine_results[0]
    improvement = (best.sharpe_ratio - coarse_results[0].sharpe_ratio) / coarse_results[0].sharpe_ratio * 100

    return {
        'strategy': strategy_type,
        'coarse_time': coarse_time,
        'fine_time': fine_time,
        'total_time': coarse_time + fine_time,
        'coarse_best_score': coarse_results[0].sharpe_ratio,
        'fine_best_score': best.sharpe_ratio,
        'improvement': improvement,
        'win_rate': best.win_rate,
        'mdd': best.max_drawdown,
        'profit_factor': best.profit_factor,
        'trades': best.trades,
        'best_params': best.params
    }


def main():
    print("MACD vs ADX Coarse-to-Fine Comparison")
    print("="*70)

    # 1. 데이터 로드
    df = load_data('bybit', 'BTCUSDT', '1h')
    if df is None:
        print("ERROR: Data loading failed")
        return 1

    # 2. MACD 테스트
    macd_result = test_strategy(df, 'macd')

    # 3. ADX 테스트
    adx_result = test_strategy(df, 'adx')

    # 4. 비교 분석
    print("\n" + "="*70)
    print("Comparison Summary")
    print("="*70)

    if macd_result and adx_result:
        print("\nMACD Strategy:")
        print(f"  Best Score: {macd_result['fine_best_score']:.2f}")
        print(f"  Win Rate: {macd_result['win_rate']:.1f}%")
        print(f"  MDD: {macd_result['mdd']:.2f}%")
        print(f"  PF: {macd_result['profit_factor']:.2f}")
        print(f"  Trades: {macd_result['trades']}")
        print(f"  Improvement: {macd_result['improvement']:+.2f}%")
        print(f"  Time: {macd_result['total_time']:.1f}s")
        print(f"  Params: {macd_result['best_params']}")

        print("\nADX Strategy:")
        print(f"  Best Score: {adx_result['fine_best_score']:.2f}")
        print(f"  Win Rate: {adx_result['win_rate']:.1f}%")
        print(f"  MDD: {adx_result['mdd']:.2f}%")
        print(f"  PF: {adx_result['profit_factor']:.2f}")
        print(f"  Trades: {adx_result['trades']}")
        print(f"  Improvement: {adx_result['improvement']:+.2f}%")
        print(f"  Time: {adx_result['total_time']:.1f}s")
        print(f"  Params: {adx_result['best_params']}")

        print("\n" + "-"*70)
        print("Key Differences:")
        print("-"*70)

        # 점수 차이
        score_diff = macd_result['fine_best_score'] - adx_result['fine_best_score']
        print(f"Score Diff (MACD - ADX): {score_diff:+.2f}")

        # 파라미터 수렴 여부
        print("\nParameter Convergence:")
        for key in ['atr_mult', 'filter_tf', 'trail_start_r', 'entry_validity_hours']:
            macd_val = macd_result['best_params'].get(key, 'N/A')
            adx_val = adx_result['best_params'].get(key, 'N/A')
            same = "(SAME)" if macd_val == adx_val else "(DIFF)"
            print(f"  {key}: MACD={macd_val} | ADX={adx_val} {same}")

    print("\n" + "="*70)
    print("Analysis Complete")
    print("="*70)

    return 0


if __name__ == '__main__':
    sys.exit(main())
