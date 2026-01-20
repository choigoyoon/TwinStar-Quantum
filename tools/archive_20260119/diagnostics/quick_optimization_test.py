#!/usr/bin/env python3
"""Quick 모드 최적화 테스트 (간소화 버전)"""
import sys
from pathlib import Path

# 프로젝트 루트 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    print("="*80)
    print("TwinStar-Quantum Quick Optimization Test")
    print("="*80)

    print("\n[1/5] Importing modules...")
    import pandas as pd
    from core.optimizer import BacktestOptimizer, generate_quick_grid, estimate_combinations
    from core.strategy_core import AlphaX7Core

    print("[2/5] Loading data...")
    cache_dir = BASE_DIR / 'data' / 'cache'
    data_file = cache_dir / 'sample_btcusdt_1h.parquet'

    if not data_file.exists():
        data_file = cache_dir / 'bybit_btcusdt_15m.parquet'

    df = pd.read_parquet(data_file)
    print(f"      Loaded: {len(df)} candles from {data_file.name}")

    # 타임스탬프 변환
    if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        first_val = df['timestamp'].iloc[0]
        if isinstance(first_val, (int, float)) and first_val > 1e12:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        elif isinstance(first_val, (int, float)):
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

    print(f"      Range: {df['timestamp'].iloc[0]} ~ {df['timestamp'].iloc[-1]}")

    print("\n[3/5] Creating Quick grid...")
    grid = generate_quick_grid('1h')
    total_combos, est_minutes = estimate_combinations(grid)
    print(f"      Combinations: {total_combos}")
    print(f"      Estimated time: ~{est_minutes:.1f} min")

    print("\n[4/5] Running optimization...")
    print("      (This may take a few minutes...)")

    import time
    optimizer = BacktestOptimizer(AlphaX7Core, df)
    start_time = time.time()

    results = optimizer.run_optimization(
        df=df,
        grid=grid,
        metric='sharpe_ratio',
        capital_mode='compound',
        n_cores=None
    )

    elapsed = time.time() - start_time

    print(f"\n[5/5] Results:")
    print(f"      Time: {elapsed/60:.1f} min ({elapsed:.1f} sec)")
    print(f"      Valid results: {len(results)}")

    if results:
        print(f"\n{'='*80}")
        print("TOP 10 RESULTS:")
        print(f"{'='*80}")

        for i, res in enumerate(results[:10], 1):
            print(f"\n[{i}] {res.grade}")
            print(f"    Win Rate: {res.win_rate:.2f}%")
            print(f"    Return: {res.compound_return:.2f}%")
            print(f"    MDD: {res.max_drawdown:.2f}%")
            print(f"    Sharpe: {res.sharpe_ratio:.2f}")
            print(f"    PF: {res.profit_factor:.2f}")
            print(f"    Trades: {res.trades} ({res.avg_trades_per_day:.2f}/day)")
            print(f"    Params: leverage={res.params.get('leverage')}, "
                  f"atr_mult={res.params.get('atr_mult')}, "
                  f"trail_start={res.params.get('trail_start_r')}")

        # 목표 달성 여부
        best = results[0]
        print(f"\n{'='*80}")
        print("TARGET ACHIEVEMENT (Best Result):")
        print(f"{'='*80}")
        print(f"Win Rate ≥ 80%:   {'✅ YES' if best.win_rate >= 80 else '❌ NO'} ({best.win_rate:.1f}%)")
        print(f"MDD ≤ 20%:        {'✅ YES' if abs(best.max_drawdown) <= 20 else '❌ NO'} ({best.max_drawdown:.1f}%)")
        print(f"Trades ≤ 0.5/day: {'✅ YES' if best.avg_trades_per_day <= 0.5 else '❌ NO'} ({best.avg_trades_per_day:.2f}/day)")

        # 승률 높은 결과 찾기
        high_winrate = sorted(results, key=lambda x: x.win_rate, reverse=True)[:3]
        print(f"\n{'='*80}")
        print("HIGH WIN RATE Results (Top 3):")
        print(f"{'='*80}")
        for i, res in enumerate(high_winrate, 1):
            print(f"{i}. Win: {res.win_rate:.1f}%, MDD: {res.max_drawdown:.1f}%, "
                  f"Trades/day: {res.avg_trades_per_day:.2f}, "
                  f"filter_tf: {res.params.get('filter_tf')}, "
                  f"atr: {res.params.get('atr_mult')}")

        # 매매빈도 낮은 결과 찾기
        low_freq = sorted(results, key=lambda x: x.avg_trades_per_day)[:3]
        print(f"\n{'='*80}")
        print("LOW FREQUENCY Results (Top 3):")
        print(f"{'='*80}")
        for i, res in enumerate(low_freq, 1):
            print(f"{i}. Trades/day: {res.avg_trades_per_day:.2f}, "
                  f"Win: {res.win_rate:.1f}%, MDD: {res.max_drawdown:.1f}%, "
                  f"filter_tf: {res.params.get('filter_tf')}, "
                  f"entry_validity: {res.params.get('entry_validity_hours')}h")

    print(f"\n{'='*80}")
    print("COMPLETE")
    print(f"{'='*80}")

except Exception as e:
    print(f"\n[ERROR] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
