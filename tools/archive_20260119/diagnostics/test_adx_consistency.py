#!/usr/bin/env python3
"""
ADX 전략 일관성 테스트 - 3회 실행하여 결과 변동 확인
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer
from core.strategy_core import AlphaX7Core
from utils.data_utils import resample_data


def main():
    print("="*70)
    print("ADX Strategy Consistency Test")
    print("="*70)

    # 데이터 로드
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
    df_15m = dm.get_full_history(with_indicators=False)

    if df_15m is None or df_15m.empty:
        print("❌ 데이터 로드 실패")
        return 1

    df = resample_data(df_15m, '1h', add_indicators=False)

    print(f"Data loaded: {len(df):,} candles")

    # Optimizer 생성
    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type='adx'
    )

    results = []

    # 3회 실행
    for i in range(3):
        print(f"\n{'='*70}")
        print(f"Run {i+1}/3")
        print(f"{'='*70}")

        # Coarse Grid
        coarse = optimizer.run_coarse_grid_optimization(
            df=df,
            trend_tf='1h',
            metric='sharpe_ratio'
        )

        # Fine Grid
        fine = optimizer.run_fine_grid_optimization(
            df=df,
            trend_tf='1h',
            coarse_results=coarse,
            top_n=20,
            metric='sharpe_ratio'
        )

        best = fine[0]

        result = {
            'run': i+1,
            'score': best.sharpe_ratio,
            'win_rate': best.win_rate,
            'mdd': best.max_drawdown,
            'pf': best.profit_factor,
            'trades': best.trades,
            'atr_mult': best.params['atr_mult'],
            'filter_tf': best.params['filter_tf'],
            'trail_start_r': best.params['trail_start_r'],
            'trail_dist_r': best.params['trail_dist_r'],
            'entry_hours': best.params['entry_validity_hours'],
            'adx_period': best.params.get('adx_period', 'N/A'),
            'adx_threshold': best.params.get('adx_threshold', 'N/A')
        }

        results.append(result)

        print(f"\nBest Result:")
        print(f"  Score: {result['score']:.2f}")
        print(f"  Win Rate: {result['win_rate']:.1f}%")
        print(f"  MDD: {result['mdd']:.2f}%")
        print(f"  PF: {result['pf']:.2f}")
        print(f"  Trades: {result['trades']}")
        print(f"\nParameters:")
        print(f"  atr_mult: {result['atr_mult']}")
        print(f"  filter_tf: {result['filter_tf']}")
        print(f"  trail_start_r: {result['trail_start_r']}")
        print(f"  trail_dist_r: {result['trail_dist_r']}")
        print(f"  entry_validity_hours: {result['entry_hours']:.1f}")
        print(f"  adx_period: {result['adx_period']}")
        print(f"  adx_threshold: {result['adx_threshold']}")

    # 결과 비교
    print(f"\n{'='*70}")
    print("Comparison Across 3 Runs")
    print(f"{'='*70}")

    print("\nScores:")
    for r in results:
        print(f"  Run {r['run']}: {r['score']:.2f}")

    scores = [r['score'] for r in results]
    score_std = pd.Series(scores).std()
    print(f"  Std Dev: {score_std:.4f}")
    print(f"  Range: {max(scores) - min(scores):.2f}")

    print("\nParameter Consistency:")
    params_to_check = ['atr_mult', 'trail_start_r', 'entry_hours', 'adx_period', 'adx_threshold']

    for param in params_to_check:
        values = [r[param] for r in results]
        unique_count = len(set(values))
        print(f"  {param}: {values} -> {unique_count} unique values")

    # 결론
    print(f"\n{'='*70}")
    print("Conclusion")
    print(f"{'='*70}")

    if score_std < 0.01 and unique_count == 1:
        print("PROBLEM: Results are identical (hardcoded behavior)")
    elif score_std < 0.5:
        print("WARNING: Results are very similar (low variance)")
    else:
        print("SUCCESS: Results show healthy variance (proper exploration)")

    print(f"\nScore Variance: {score_std:.4f}")
    print(f"Parameter Diversity: {unique_count}/{len(params_to_check)} params vary")

    return 0


if __name__ == '__main__':
    sys.exit(main())
