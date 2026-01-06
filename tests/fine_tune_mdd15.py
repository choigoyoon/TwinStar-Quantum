"""파라미터 미세 조정 테스트 - MDD 15% 목표"""
import sys
sys.path.insert(0, '.')
import os
os.chdir('C:\\매매전략')

def main():
    import pandas as pd
    import time
    import itertools
    
    print("=" * 60)
    print("        파라미터 미세 조정 - MDD 15% 목표")
    print("=" * 60 + "\n")

    # 데이터 로드
    df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    df_1h = df.resample('1h').agg({
        'open': 'first', 'high': 'max', 
        'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()
    
    print(f"데이터: {len(df_1h):,} 캔들 (1H)\n")

    from core.strategy_core import AlphaX7Core
    
    # 미세 조정 파라미터 그리드
    # 현재 베스트: filter_tf=6h, atr_mult=1.0, trail_start=0.5, trail_dist=0.1
    fine_grid = {
        'filter_tf': ['4h', '6h'],                      # 2
        'atr_mult': [0.9, 0.95, 1.0, 1.05, 1.1],       # 5 (더 세밀하게)
        'trail_start_r': [0.4, 0.5, 0.6, 0.7],         # 4
        'trail_dist_r': [0.08, 0.1, 0.12],             # 3
        'entry_validity_hours': [6.0, 12.0, 24.0],     # 3
        'pullback_rsi_long': [35, 40],                  # 2
        'pullback_rsi_short': [60, 65],                 # 2
    }
    
    # 조합 수 계산
    total_combos = 1
    for v in fine_grid.values():
        total_combos *= len(v)
    print(f"총 조합 수: {total_combos:,}\n")
    
    # 전체 탐색
    strategy = AlphaX7Core(use_mtf=True)
    
    results = []
    keys = list(fine_grid.keys())
    combos = list(itertools.product(*fine_grid.values()))
    
    start = time.time()
    
    for i, combo in enumerate(combos):
        params = {
            'pattern_tolerance': 0.05,
            'slippage': 0.0006,
        }
        for j, key in enumerate(keys):
            params[key] = combo[j]
        
        trades = strategy.run_backtest(
            df_pattern=df_1h,
            df_entry=df_1h,
            **params
        )
        
        if trades and len(trades) >= 10:
            pnls = [t['pnl'] for t in trades]
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p < 0]
            
            win_rate = len(wins) / len(trades) * 100
            total_return = sum(pnls)
            
            # MDD 계산
            equity = 1.0
            peak = 1.0
            mdd = 0
            for p in pnls:
                equity *= (1 + p/100)
                if equity > peak:
                    peak = equity
                dd = (peak - equity) / peak * 100
                if dd > mdd:
                    mdd = dd
            
            # PF 계산
            gains = sum(wins) if wins else 0
            loss_sum = abs(sum(losses)) if losses else 0
            pf = gains / loss_sum if loss_sum > 0.01 else gains
            
            # MDD 20% 이하만 저장
            if mdd <= 25.0 and pf >= 1.0:
                results.append({
                    'params': params.copy(),
                    'trades': len(trades),
                    'win_rate': win_rate,
                    'return': total_return,
                    'mdd': mdd,
                    'pf': pf,
                })
        
        if (i + 1) % 100 == 0:
            elapsed = time.time() - start
            eta = elapsed / (i + 1) * (total_combos - i - 1)
            print(f"  진행: {i+1}/{total_combos} ({(i+1)/total_combos*100:.1f}%) - 발견: {len(results)}개 - ETA: {eta:.0f}초")
    
    elapsed = time.time() - start
    print(f"\n완료: {elapsed:.1f}초, 유효 결과: {len(results)}개\n")
    
    if not results:
        print("❌ 유효 결과 없음")
        return
    
    # MDD 기준 정렬 (낮은 순)
    results_by_mdd = sorted(results, key=lambda x: x['mdd'])
    
    print("=" * 60)
    print("         Top 10 (MDD 낮은 순)")
    print("=" * 60)
    print(f"{'순위':>4} {'MDD':>7} {'승률':>7} {'수익률':>10} {'PF':>6} {'거래':>5}")
    print("-" * 60)
    
    for i, r in enumerate(results_by_mdd[:10]):
        print(f"{i+1:>4} {r['mdd']:>6.1f}% {r['win_rate']:>6.1f}% {r['return']:>9.1f}% {r['pf']:>6.2f} {r['trades']:>5}")
    
    # 최고 결과 상세
    best = results_by_mdd[0]
    print("\n" + "=" * 60)
    print("             🏆 최고 결과 (최저 MDD)")
    print("=" * 60)
    print(f"  MDD:    {best['mdd']:.1f}%")
    print(f"  승률:   {best['win_rate']:.1f}%")
    print(f"  수익률: {best['return']:.1f}%")
    print(f"  PF:     {best['pf']:.2f}")
    print(f"  거래수: {best['trades']}")
    print("\n  파라미터:")
    for k, v in best['params'].items():
        if k not in ['pattern_tolerance', 'slippage']:
            print(f"    {k}: {v}")
    
    # MDD 15% 이하 결과
    under_15 = [r for r in results_by_mdd if r['mdd'] <= 15.0]
    if under_15:
        print(f"\n✅ MDD ≤15% 결과: {len(under_15)}개 발견!")
    else:
        print(f"\n⚠️ MDD ≤15% 결과 없음. 최저 MDD: {results_by_mdd[0]['mdd']:.1f}%")

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
