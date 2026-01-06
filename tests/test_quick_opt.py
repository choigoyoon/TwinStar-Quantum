"""빠른 최적화 테스트 (Windows 호환)"""
import sys
sys.path.insert(0, '.')
import os
os.chdir('C:\\매매전략')

def main():
    import pandas as pd
    
    print("=== 빠른 최적화 테스트 ===\n")

    # 1. 데이터 로드 + 리샘플링
    df = pd.read_parquet('data/cache/bybit_btcusdt_15m.parquet')
    print(f"15m 데이터: {len(df):,} 캔들")

    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df = df.set_index('timestamp')
    df_1h = df.resample('1h').agg({
        'open': 'first', 'high': 'max', 
        'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()

    # 최근 3000개만 사용 (속도)
    df_test = df_1h.tail(3000)
    print(f"테스트 데이터: {len(df_test)} 캔들 (1H)\n")

    # 2. 최적화 실행
    from core.optimizer import BacktestOptimizer, generate_quick_grid
    from core.strategy_core import AlphaX7Core

    optimizer = BacktestOptimizer(AlphaX7Core, df_test)

    # Quick 그리드 생성
    grid = generate_quick_grid('1h', 20.0)
    print(f"Grid 파라미터: {list(grid.keys())}")

    # 조합 수 계산
    total = 1
    for v in grid.values():
        total *= len(v)
    print(f"총 조합 수: {total}\n")

    print("최적화 시작...\n")
    results = optimizer.optimize(grid, metric='sharpe', slippage=0.0005, fee=0.0006, n_cores=4)

    # 3. 결과 출력
    print(f"\n=== 결과 ({len(results)}개) ===\n")

    for i, r in enumerate(results[:10]):
        print(f"{i+1}. {r.strategy_type or '일반'} [{r.grade}]")
        print(f"   승률: {r.win_rate:.1f}% | 수익: {r.total_return:.1f}% | MDD: {r.max_drawdown:.1f}%")
        print(f"   PF: {r.profit_factor:.2f} | 샤프: {r.sharpe_ratio:.1f} | 거래: {r.trades}")
        print(f"   일평균: {r.avg_trades_per_day:.2f}회 | 안정성: {r.stability}")
        print()

    print("✅ 테스트 완료!")

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    main()
