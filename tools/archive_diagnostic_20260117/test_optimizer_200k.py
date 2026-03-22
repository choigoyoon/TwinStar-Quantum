#!/usr/bin/env python3
"""간단한 최적화 테스트 (이모지/한글 제거)"""
import sys
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

print("="*80)
print("Quick Optimization Test (v2.1)")
print("="*80)

try:
    print("\n[1/5] Loading modules...")
    import pandas as pd
    import time
    from core.optimizer import BacktestOptimizer, generate_quick_grid, estimate_combinations
    from core.strategy_core import AlphaX7Core

    print("[2/5] Loading data...")
    cache_dir = BASE_DIR / 'data' / 'cache'
    data_file = cache_dir / 'bybit_btcusdt_15m.parquet'

    if not data_file.exists():
        data_file = cache_dir / 'sample_btcusdt_1h.parquet'

    df = pd.read_parquet(data_file)

    # Timestamp conversion
    if 'timestamp' in df.columns:
        first_val = df['timestamp'].iloc[0]
        if isinstance(first_val, (int, float)) and first_val > 1e12:
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        elif isinstance(first_val, (int, float)):
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

    print("      File: {}".format(data_file.name))
    print("      Rows: {:,}".format(len(df)))
    print("      Range: {} ~ {}".format(df['timestamp'].iloc[0], df['timestamp'].iloc[-1]))

    print("\n[3/5] Creating grid...")
    grid = generate_quick_grid('1h')
    total_combos, est_minutes = estimate_combinations(grid)
    print("      Combinations: {}".format(total_combos))
    print("      Estimated time: ~{:.1f} min".format(est_minutes))

    print("\n[4/5] Running optimization...")
    print("      (This may take a few minutes...)")

    optimizer = BacktestOptimizer(AlphaX7Core, df)
    start_time = time.time()

    # Single-threaded to avoid multiprocessing issues
    results = optimizer.run_optimization(
        df=df,
        grid=grid,
        metric='sharpe_ratio',
        capital_mode='compound',
        n_cores=1
    )

    elapsed = time.time() - start_time

    print("\n[5/5] Results:")
    print("      Time: {:.1f} min ({:.1f} sec)".format(elapsed/60, elapsed))
    print("      Valid results: {}".format(len(results)))

    if results:
        print("\n" + "="*80)
        print("TOP 10 RESULTS:")
        print("="*80)

        for i, res in enumerate(results[:10], 1):
            print("\n[{}] Grade: {}".format(i, res.grade))
            print("    Win Rate: {:.2f}%".format(res.win_rate))
            print("    Return: {:.2f}%".format(res.compound_return))
            print("    MDD: {:.2f}%".format(res.max_drawdown))
            print("    Sharpe: {:.2f}".format(res.sharpe_ratio))
            print("    PF: {:.2f}".format(res.profit_factor))
            print("    Trades: {} ({:.2f}/day)".format(res.trades, res.avg_trades_per_day))
            print("    Params:")
            print("      - filter_tf: {}".format(res.params.get('filter_tf')))
            print("      - leverage: {}".format(res.params.get('leverage')))
            print("      - atr_mult: {}".format(res.params.get('atr_mult')))
            print("      - trail_start_r: {}".format(res.params.get('trail_start_r')))

        # Target check
        best = results[0]
        print("\n" + "="*80)
        print("TARGET ACHIEVEMENT (Best Result):")
        print("="*80)
        print("Win Rate >= 80%:   {} ({:.1f}%)".format('YES' if best.win_rate >= 80 else 'NO', best.win_rate))
        print("MDD <= 20%:        {} ({:.1f}%)".format('YES' if abs(best.max_drawdown) <= 20 else 'NO', best.max_drawdown))
        print("Trades <= 0.5/day: {} ({:.2f}/day)".format('YES' if best.avg_trades_per_day <= 0.5 else 'NO', best.avg_trades_per_day))

        # High win rate
        high_winrate = sorted(results, key=lambda x: x.win_rate, reverse=True)[:3]
        print("\n" + "="*80)
        print("HIGH WIN RATE Results (Top 3):")
        print("="*80)
        for i, res in enumerate(high_winrate, 1):
            print("{}. Win: {:.1f}%, MDD: {:.1f}%, Trades/day: {:.2f}".format(i, res.win_rate, res.max_drawdown, res.avg_trades_per_day))
            print("   filter_tf: {}, atr: {}".format(res.params.get('filter_tf'), res.params.get('atr_mult')))

        # Low frequency
        low_freq = sorted(results, key=lambda x: x.avg_trades_per_day)[:3]
        print("\n" + "="*80)
        print("LOW FREQUENCY Results (Top 3):")
        print("="*80)
        for i, res in enumerate(low_freq, 1):
            print("{}. Trades/day: {:.2f}, Win: {:.1f}%, MDD: {:.1f}%".format(i, res.avg_trades_per_day, res.win_rate, res.max_drawdown))
            print("   filter_tf: {}, entry_validity: {}h".format(res.params.get('filter_tf'), res.params.get('entry_validity_hours')))

    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)

except Exception as e:
    print("\n[ERROR] {}".format(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)
