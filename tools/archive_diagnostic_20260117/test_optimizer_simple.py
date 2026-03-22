#!/usr/bin/env python3
"""
Simple optimization test (v3.0)
- Quick mode: 1개 결과 (최적)
- Standard mode: 3개 결과 (공격, 균형, 보수)
- Deep mode: 5개+ 결과 (관리자 권한 필요)
"""
import sys
from pathlib import Path

def main():
    BASE_DIR = Path(__file__).parent.parent
    sys.path.insert(0, str(BASE_DIR))

    print("="*80)
    print("Quick Optimization Test (v3.0)")
    print("="*80)

    try:
        print("\n[1/5] Loading modules...")
        import pandas as pd
        import time
        from core.optimizer import (
            BacktestOptimizer, 
            generate_quick_grid,
            get_mode_from_grid,
            MODE_RESULT_COUNT
        )
        from core.strategy_core import AlphaX7Core

        print("[2/5] Loading data...")
        cache_dir = BASE_DIR / 'data' / 'cache'
        data_file = cache_dir / 'bybit_btcusdt_15m.parquet'

        if not data_file.exists():
            data_file = cache_dir / 'sample_btcusdt_1h.parquet'

        df = pd.read_parquet(data_file)

        if 'timestamp' in df.columns:
            first_val = df['timestamp'].iloc[0]
            if isinstance(first_val, (int, float)) and first_val > 1e12:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            elif isinstance(first_val, (int, float)):
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')

        print("      File: {}".format(data_file.name))
        print("      Rows: {:,}".format(len(df)))

        print("\n[3/5] Creating grid...")
        grid = generate_quick_grid('1h')
        
        # 자동 모드 감지
        mode = get_mode_from_grid(grid)
        expected_results = MODE_RESULT_COUNT.get(mode, 3)
        
        # 조합 수 계산
        total_combinations = 1
        for values in grid.values():
            if isinstance(values, list):
                total_combinations *= len(values)
        
        print("      Mode: {} (결과 {}개)".format(mode.upper(), expected_results))
        print("      Combinations: {}".format(total_combinations))

        print("\n[4/5] Running optimization...")
        print("      (This may take 2-5 minutes...)")

        optimizer = BacktestOptimizer(AlphaX7Core, df)
        start_time = time.time()

        results = optimizer.run_optimization(
            df=df,
            grid=grid,
            metric='sharpe_ratio',
            capital_mode='compound',
            n_cores=1,
            mode=mode  # 모드 전달
        )

        elapsed = time.time() - start_time

        print("\n[5/5] Results:")
        print("      Time: {:.1f} min ({:.1f} sec)".format(elapsed/60, elapsed))
        print("      Valid results: {}".format(len(results)))

        if results:
            # ============ 대표 결과 출력 (모드별) ============
            print("\n" + "="*80)
            print("📊 REPRESENTATIVE RESULTS ({} Mode)".format(mode.upper()))
            print("="*80)
            
            # 전략 유형이 있는 결과만 필터링 (대표 결과)
            reps = [r for r in results if r.strategy_type][:expected_results]
            
            for i, res in enumerate(reps, 1):
                print("\n[{}] {} {}".format(i, res.strategy_type, res.grade))
                print("    Win Rate: {:.2f}%".format(res.win_rate))
                print("    Return: {:.2f}% (CAGR: {:.2f}%)".format(res.compound_return, res.cagr))
                print("    Avg PnL: {:.4f}% (Goal: 0.5%)".format(res.avg_pnl))
                print("    MDD: {:.2f}%".format(res.max_drawdown))
                print("    Sharpe: {:.2f}".format(res.sharpe_ratio))
                print("    PF: {:.2f}".format(res.profit_factor))
                print("    Trades: {} ({:.2f}/day)".format(res.trades, res.avg_trades_per_day))
                print("    Params: filter_tf={}, leverage={}, atr={}".format(
                    res.params.get('filter_tf'), 
                    res.params.get('leverage'), 
                    res.params.get('atr_mult')))

            # ============ 상위 10개 전체 결과 ============
            print("\n" + "="*80)
            print("📈 TOP 10 ALL RESULTS:")
            print("="*80)

            for i, res in enumerate(results[:10], 1):
                type_label = res.strategy_type if res.strategy_type else ""
                print("\n[{}] {} {}".format(i, type_label, res.grade))
                print("    Win Rate: {:.2f}%".format(res.win_rate))
                print("    Return: {:.2f}% (CAGR: {:.2f}%)".format(res.compound_return, res.cagr))
                print("    Avg PnL: {:.4f}%".format(res.avg_pnl))
                print("    MDD: {:.2f}%".format(res.max_drawdown))
                print("    Sharpe: {:.2f}".format(res.sharpe_ratio))
                print("    PF: {:.2f}".format(res.profit_factor))
                print("    Trades: {} ({:.2f}/day)".format(res.trades, res.avg_trades_per_day))
                print("    Params: filter_tf={}, leverage={}, atr={}".format(
                    res.params.get('filter_tf'), 
                    res.params.get('leverage'), 
                    res.params.get('atr_mult')))

            # ============ 목표 달성 체크 ============
            best = results[0]
            print("\n" + "="*80)
            print("🎯 TARGET ACHIEVEMENT:")
            print("="*80)
            print("Win Rate >= 80%:   {} ({:.1f}%)".format('YES ✅' if best.win_rate >= 80 else 'NO ❌', best.win_rate))
            print("MDD <= 20%:        {} ({:.1f}%)".format('YES ✅' if abs(best.max_drawdown) <= 20 else 'NO ❌', best.max_drawdown))
            print("Trades <= 0.5/day: {} ({:.2f}/day)".format('YES ✅' if best.avg_trades_per_day <= 0.5 else 'NO ❌', best.avg_trades_per_day))

            # ============ 추가 분석 ============
            high_winrate = sorted(results, key=lambda x: x.win_rate, reverse=True)[:3]
            print("\n" + "="*80)
            print("🏆 HIGH WIN RATE Top 3:")
            print("="*80)
            for i, res in enumerate(high_winrate, 1):
                print("{}. Win: {:.1f}%, MDD: {:.1f}%, Trades/day: {:.2f}, filter_tf: {}".format(
                    i, res.win_rate, res.max_drawdown, res.avg_trades_per_day, res.params.get('filter_tf')))

            low_freq = sorted(results, key=lambda x: x.avg_trades_per_day)[:3]
            print("\n" + "="*80)
            print("🐢 LOW FREQUENCY Top 3:")
            print("="*80)
            for i, res in enumerate(low_freq, 1):
                print("{}. Trades/day: {:.2f}, Win: {:.1f}%, MDD: {:.1f}%, filter_tf: {}".format(
                    i, res.avg_trades_per_day, res.win_rate, res.max_drawdown, res.params.get('filter_tf')))

        print("\n" + "="*80)
        print("✅ COMPLETE")
        print("="*80)

    except Exception as e:
        print("\n[ERROR] {}".format(e))
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
