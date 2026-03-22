#!/usr/bin/env python3
"""
ADX Threshold 영향 테스트
프리셋 값 (10.0) vs 최적화 값 (18-25) 비교
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_manager import BotDataManager
from core.optimizer import BacktestOptimizer
from core.strategy_core import AlphaX7Core
from utils.data_utils import resample_data


def main():
    print("="*70)
    print("ADX Threshold Impact Test")
    print("="*70)

    # 데이터 로드
    dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '15m'})
    df_15m = dm.get_full_history(with_indicators=False)

    if df_15m is None or df_15m.empty:
        print("❌ 데이터 로드 실패")
        return 1

    df = resample_data(df_15m, '1h', add_indicators=False)

    print(f"Data: {len(df):,} candles\n")

    optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type='adx'
    )

    print("Testing Coarse Grid with new threshold range...")
    print("-"*70)

    # Coarse Grid (수정된 범위로)
    coarse = optimizer.run_coarse_grid_optimization(
        df=df,
        trend_tf='1h',
        metric='sharpe_ratio'
    )

    # 상위 10개 결과 분석
    print("\n" + "="*70)
    print("Top 10 Results (ADX Threshold Distribution)")
    print("="*70)

    threshold_counts = {}
    for i, result in enumerate(coarse[:10], 1):
        threshold = result.params.get('adx_threshold', 'N/A')
        threshold_counts[threshold] = threshold_counts.get(threshold, 0) + 1

        print(f"\n{i}. Score: {result.sharpe_ratio:.2f}")
        print(f"   Trades: {result.trades}")
        print(f"   Win Rate: {result.win_rate:.1f}%")
        print(f"   MDD: {result.max_drawdown:.2f}%")
        print(f"   ADX Threshold: {threshold}")
        print(f"   ADX Period: {result.params.get('adx_period', 'N/A')}")

    print("\n" + "="*70)
    print("Threshold Distribution in Top 10")
    print("="*70)
    for threshold, count in sorted(threshold_counts.items()):
        print(f"  {threshold}: {count} times ({count*10}%)")

    # 임계값별 거래 빈도 분석
    print("\n" + "="*70)
    print("Trade Frequency by Threshold")
    print("="*70)

    threshold_groups = {10.0: [], 18.0: [], 25.0: []}
    for result in coarse[:50]:  # 상위 50개
        threshold = result.params.get('adx_threshold')
        if threshold in threshold_groups:
            threshold_groups[threshold].append(result.trades)

    for threshold, trades_list in sorted(threshold_groups.items()):
        if trades_list:
            avg_trades = sum(trades_list) / len(trades_list)
            print(f"  Threshold {threshold}: avg {avg_trades:.0f} trades ({len(trades_list)} samples)")

    print("\n" + "="*70)
    print("Conclusion")
    print("="*70)

    top_threshold = coarse[0].params.get('adx_threshold')
    top_trades = coarse[0].trades

    print(f"Best Result: Threshold {top_threshold}, {top_trades} trades")

    if top_threshold is not None:
        if top_threshold == 10.0:
            print("SUCCESS: Lower threshold (10.0) found optimal")
            print("         -> Higher trade frequency expected")
        elif top_threshold >= 18.0:
            print("NOTE: Higher threshold still optimal")
            print("      -> Conservative strategy preferred by data")
    else:
        print("WARNING: No adx_threshold found in parameters")

    return 0


if __name__ == '__main__':
    sys.exit(main())
