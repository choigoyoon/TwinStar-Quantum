"""모드별 순차 최적화 실제 테스트"""
import sys
sys.path.insert(0, '.')
import os
os.chdir('C:\\매매전략')

def main():
    import pandas as pd
    import time
    
    print("=" * 55)
    print("    모드별 순차 최적화 실제 테스트")
    print("=" * 55 + "\n")

    # 데이터 로드 (작은 셋)
    df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    df_1h = df.resample('1h').agg({
        'open': 'first', 'high': 'max', 
        'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()

    df_test = df_1h  # 전체 데이터 사용
    print(f"테스트 데이터: {len(df_test):,} 캔들 (1H) - 전체\n")

    from core.optimization_logic import OptimizationEngine

    results = []
    
    for mode in ['quick', 'standard', 'deep']:
        mode_icons = {'quick': '⚡', 'standard': '📊', 'deep': '🔬'}
        icon = mode_icons[mode]
        
        print(f"--- {icon} {mode.upper()} 모드 시작 ---")
        
        engine = OptimizationEngine()
        
        total_combos = 0
        def counter(stage, msg, params):
            nonlocal total_combos
            print(f"  Stage {stage}: {msg}")
        
        start = time.time()
        result = engine.run_staged_optimization(
            df=df_test,
            target_mdd=20.0,
            max_workers=4,
            stage_callback=counter,
            mode=mode
        )
        elapsed = time.time() - start
        
        if result and result.get('final_result'):
            r = result['final_result']
            print(f"  결과: 수익 {r.simple_return:.1f}%, 승률 {r.win_rate:.1f}%")
            print(f"  소요: {elapsed:.1f}초, 조합: {result.get('total_combinations', 'N/A')}")
            results.append({
                'mode': mode,
                'icon': icon,
                'return': r.simple_return,
                'win_rate': r.win_rate,
                'time': elapsed,
                'combos': result.get('total_combinations', 0)
            })
        else:
            print(f"  결과: 없음 (필터 미통과)")
            results.append({
                'mode': mode,
                'icon': icon,
                'return': 0,
                'win_rate': 0,
                'time': elapsed,
                'combos': 0
            })
        print()

    # 비교 요약
    print("=" * 55)
    print("                   비교 요약")
    print("=" * 55)
    print(f"{'모드':<12} {'조합':>6} {'시간':>8} {'수익률':>10} {'승률':>8}")
    print("-" * 55)
    for r in results:
        print(f"{r['icon']} {r['mode']:<8} {r['combos']:>6} {r['time']:>7.1f}s {r['return']:>9.1f}% {r['win_rate']:>7.1f}%")
    
    print("\n✅ 모드별 순차 최적화 테스트 완료!")

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
