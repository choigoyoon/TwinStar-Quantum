"""빠른/일반/심층 최적화 비교 테스트"""
import sys
sys.path.insert(0, '.')
import os
os.chdir('C:\\매매전략')

def main():
    import pandas as pd
    import time
    
    print("=" * 60)
    print("     빠른 / 일반 / 심층 최적화 비교 테스트")
    print("=" * 60 + "\n")

    # 데이터 로드
    df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    df_1h = df.resample('1h').agg({
        'open': 'first', 'high': 'max', 
        'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()

    df_test = df_1h.tail(2000)  # 속도를 위해 2000개
    print(f"테스트 데이터: {len(df_test)} 캔들 (1H)\n")

    from typing import Any, cast
    from core.optimizer import (
        BacktestOptimizer, 
        generate_quick_grid, 
        generate_standard_grid, 
        generate_deep_grid
    )
    from core.strategy_core import AlphaX7Core

    results_summary = []
    
    # 각 모드별 테스트
    modes = [
        ('⚡ 빠른', generate_quick_grid),
        ('📊 일반', generate_standard_grid),
        ('🔬 심층', generate_deep_grid),
    ]
    
    for mode_name, grid_func in modes:
        print("-" * 50)
        print(f"{mode_name} 모드 시작...")
        
        grid = grid_func('1h', 20.0)
        
        # 조합 수 계산
        total = 1
        for v in grid.values():
            total *= len(v)
        print(f"조합 수: {total}")
        
        # 심층은 너무 오래 걸리므로 일부만
        if total > 1000:
            print(f"⚠️ 조합이 많아서 일부만 테스트 (최대 500개)")
            # 그리드 축소
            for key in grid:
                if len(grid[key]) > 2:
                    grid[key] = grid[key][:2]
            total = 1
            for v in grid.values():
                total *= len(v)
            print(f"축소된 조합 수: {total}")
        
        optimizer = BacktestOptimizer(AlphaX7Core, df_test)
        
        start = time.time()
        results = cast(Any, optimizer).optimize(grid, metric='sharpe', slippage=0.0005, fee=0.0006, n_cores=4)
        elapsed = time.time() - start
        
        # 최고 결과
        if results:
            best = results[0]
            results_summary.append({
                'mode': mode_name,
                'combos': total,
                'passed': len(results),
                'time': elapsed,
                'best_return': best.total_return,
                'best_wr': best.win_rate,
                'best_mdd': best.max_drawdown,
                'best_pf': best.profit_factor,
                'best_grade': best.grade
            })
            print(f"결과: {len(results)}개 통과, {elapsed:.1f}초")
            print(f"최고: {best.total_return:.1f}% 수익, {best.win_rate:.1f}% 승률, {best.grade}")
        else:
            results_summary.append({
                'mode': mode_name,
                'combos': total,
                'passed': 0,
                'time': elapsed,
                'best_return': 0,
                'best_wr': 0,
                'best_mdd': 0,
                'best_pf': 0,
                'best_grade': 'N/A'
            })
            print(f"결과: 통과 없음, {elapsed:.1f}초")
        print()

    # 비교 요약
    print("=" * 60)
    print("                    비교 요약")
    print("=" * 60)
    print(f"{'모드':<10} {'조합수':>8} {'통과':>6} {'시간':>8} {'수익률':>10} {'승률':>8} {'등급':>6}")
    print("-" * 60)
    
    for r in results_summary:
        print(f"{r['mode']:<10} {r['combos']:>8} {r['passed']:>6} {r['time']:>7.1f}s {r['best_return']:>9.1f}% {r['best_wr']:>7.1f}% {r['best_grade']:>6}")
    
    print("\n✅ 비교 테스트 완료!")

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
