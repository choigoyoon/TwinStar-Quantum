# C:\매매전략\verify_batch_optimizer.py
def run_verification():
    print("=== 배치 최적화 검증 ===\n")

    # 1. 임포트 확인
    print("[1] 임포트 확인...")
    try:
        from core.batch_optimizer import BatchOptimizer
        from core.optimizer import generate_standard_grid, BacktestOptimizer
        from core.strategy_core import AlphaX7Core
        print("    ✅ 모든 임포트 성공")
    except Exception as e:
        print(f"    ❌ 임포트 실패: {e}")

    # 2. 그리드 생성 확인
    print("\n[2] 그리드 생성 확인...")
    grid_4h = generate_standard_grid('4h', max_mdd=100.0)
    grid_1d = generate_standard_grid('1d', max_mdd=100.0)

    total_4h = 1
    total_1d = 1
    for v in grid_4h.values():
        if isinstance(v, list): total_4h *= len(v)
    for v in grid_1d.values():
        if isinstance(v, list): total_1d *= len(v)

    print(f"    4H 그리드: {total_4h}개 조합")
    print(f"    1D 그리드: {total_1d}개 조합")

    if total_4h >= 3000:
        print("    ✅ 정밀 그리드 적용됨")
    else:
        print("    ⚠️ 그리드 조합 부족")

    # 3. 배치 옵티마이저 설정 확인
    print("\n[3] BatchOptimizer 설정 확인...")
    bo = BatchOptimizer()
    print(f"    거래소: {getattr(bo, 'exchange', 'N/A')}")
    print(f"    타임프레임: {getattr(bo, 'timeframes', 'N/A')}")

    # 4. 싱글 심볼 테스트 (BTCUSDT 4H)
    print("\n[4] 싱글 심볼 테스트 (BTCUSDT 4H)...")
    print("    ⏳ 10~15분 소요 예상...")

    import time
    start = time.time()

    try:
        # 테스트 실행 (1개 심볼만)
        bo.symbols = ['BTCUSDT']
        bo.timeframes = ['4h']
        
        # optimize_symbol 직접 호출
        result = bo.optimize_symbol('BTCUSDT', '4h')
        
        elapsed = time.time() - start
        
        if result:
            print(f"    ✅ 최적화 성공!")
            print(f"    승률: {result.get('win_rate', 'N/A')}%")
            print(f"    PF: {result.get('profit_factor', 'N/A')}")
            print(f"    MDD: {result.get('max_drawdown', 'N/A')}%")
            print(f"    거래수: {result.get('trades', 'N/A')}")
            print(f"    소요시간: {elapsed/60:.1f}분")
        else:
            print(f"    ⚠️ 결과 없음 (소요: {elapsed/60:.1f}분)")
            
    except Exception as e:
        print(f"    ❌ 테스트 실패: {e}")

    print("\n=== 검증 완료 ===")

if __name__ == "__main__":
    run_verification()
