"""빠른/일반/심층 최적화 전체 비교 (축소 없음)"""
import sys
sys.path.insert(0, '.')
import os
os.chdir('C:\\매매전략')

def main():
    import pandas as pd
    import time
    
    print("=" * 60)
    print("   빠른 / 일반 / 심층 최적화 전체 비교 (축소 없음)")
    print("=" * 60 + "\n")

    # 데이터 로드
    df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    df_1h = df.resample('1h').agg({
        'open': 'first', 'high': 'max', 
        'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()

    df_test = df_1h.tail(1500)  # 1500개로 약간 줄임
    print(f"테스트 데이터: {len(df_test)} 캔들 (1H)\n")

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
        print(f"전체 조합 수: {total:,}")
        
        optimizer = BacktestOptimizer(AlphaX7Core, df_test)
        
        start = time.time()
        results = optimizer.optimize(grid, metric='sharpe', slippage=0.0005, fee=0.0006, n_cores=8)
        elapsed = time.time() - start
        
        # 최고 결과
        if results:
            best = results[0]
            # 스타일별 결과 수 세기
            styles = {}
            for r in results[:30]:
                st = r.strategy_type or '일반'
                styles[st] = styles.get(st, 0) + 1
            
            results_summary.append({
                'mode': mode_name,
                'combos': total,
                'passed': len(results),
                'time': elapsed,
                'best_return': best.total_return,
                'best_wr': best.win_rate,
                'best_mdd': best.max_drawdown,
                'best_pf': best.profit_factor,
                'best_grade': best.grade,
                'styles': styles
            })
            print(f"결과: {len(results):,}개 통과, {elapsed:.1f}초")
            print(f"최고: {best.total_return:.1f}% 수익, {best.win_rate:.1f}% 승률, {best.grade}")
            print(f"스타일: {styles}")
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
                'best_grade': 'N/A',
                'styles': {}
            })
            print(f"결과: 통과 없음, {elapsed:.1f}초")
        print()

    # 비교 요약
    print("=" * 70)
    print("                         비교 요약")
    print("=" * 70)
    print(f"{'모드':<10} {'조합수':>12} {'통과':>8} {'시간':>10} {'수익률':>10} {'승률':>8} {'MDD':>8} {'등급':>6}")
    print("-" * 70)
    
    for r in results_summary:
        print(f"{r['mode']:<10} {r['combos']:>12,} {r['passed']:>8,} {r['time']:>9.1f}s {r['best_return']:>9.1f}% {r['best_wr']:>7.1f}% {r['best_mdd']:>7.1f}% {r['best_grade']:>6}")
    
    print("\n" + "=" * 70)
    print("                     상위 결과 비교")
    print("=" * 70)
    
    for r in results_summary:
        print(f"\n{r['mode']} 스타일 분포: {r.get('styles', {})}")
    
    print("\n✅ 전체 비교 테스트 완료!")

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
