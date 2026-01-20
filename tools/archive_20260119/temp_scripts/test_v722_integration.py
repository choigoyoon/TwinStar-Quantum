"""v7.22 통합 테스트 - 그리드 Meta + 타임스탬프

새로 구현한 기능들을 End-to-End로 검증합니다:
1. 그리드 기반 Meta 최적화 (3단계 적응형 그리드)
2. optimal_params 출력 (단일 최적값)
3. 타임스탬프 정보 (백테스트 기간)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def test_timestamp_extraction():
    """타임스탬프 추출 테스트"""
    print("=== 타임스탬프 추출 테스트 ===\n")

    from core.optimizer import extract_timestamps_from_trades

    # 더미 거래 데이터
    start_date = datetime(2024, 1, 1)
    trades = []

    for i in range(10):
        entry_time = start_date + timedelta(days=i * 3)
        exit_time = entry_time + timedelta(hours=12)

        trades.append({
            'entry_time': entry_time.strftime('%Y-%m-%d %H:%M:%S'),
            'exit_time': exit_time.strftime('%Y-%m-%d %H:%M:%S'),
            'pnl': np.random.randn() * 10
        })

    # 타임스탬프 추출
    start_time, end_time, duration = extract_timestamps_from_trades(trades)

    print(f"Start Time: {start_time}")
    print(f"End Time: {end_time}")
    print(f"Duration: {duration} days")

    # 검증
    assert start_time is not None, "Start time is None"
    assert end_time is not None, "End time is None"
    assert duration > 0, f"Duration is invalid: {duration}"

    print("\n[SUCCESS] 타임스탬프 추출 성공")


def test_optimization_result_with_timestamps():
    """OptimizationResult 타임스탬프 필드 테스트"""
    print("\n=== OptimizationResult 타임스탬프 필드 테스트 ===\n")

    from core.optimizer import OptimizationResult
    import pandas as pd

    # OptimizationResult 생성 (타임스탬프 포함)
    result = OptimizationResult(
        params={'atr_mult': 1.5, 'filter_tf': '4h'},
        trades=100,
        win_rate=80.0,
        total_return=100.0,
        simple_return=100.0,
        compound_return=110.0,
        max_drawdown=10.0,
        sharpe_ratio=2.5,
        profit_factor=4.0,
        backtest_start_time=pd.Timestamp('2024-01-01'),
        backtest_end_time=pd.Timestamp('2024-03-01'),
        backtest_duration_days=60
    )

    # 필드 확인
    assert hasattr(result, 'backtest_start_time'), "backtest_start_time 필드 누락"
    assert hasattr(result, 'backtest_end_time'), "backtest_end_time 필드 누락"
    assert hasattr(result, 'backtest_duration_days'), "backtest_duration_days 필드 누락"

    print(f"Backtest Start: {result.backtest_start_time}")
    print(f"Backtest End: {result.backtest_end_time}")
    print(f"Duration: {result.backtest_duration_days} days")

    assert result.backtest_duration_days == 60, f"Duration 불일치: {result.backtest_duration_days}"

    print("\n[SUCCESS] OptimizationResult 타임스탬프 필드 검증 완료")


def test_grid_meta_with_timestamps():
    """그리드 Meta + 타임스탬프 통합 테스트"""
    print("\n=== 그리드 Meta + 타임스탬프 통합 테스트 ===\n")

    from core.meta_optimizer import MetaOptimizer
    from core.optimizer import BacktestOptimizer
    from core.strategy_core import AlphaX7Core
    import pandas as pd

    # 1. 더미 데이터 생성 (500개 캔들, 빠른 테스트)
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=500, freq='15min')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 50000 + np.random.randn(500) * 1000,
        'high': 50100 + np.random.randn(500) * 1000,
        'low': 49900 + np.random.randn(500) * 1000,
        'close': 50000 + np.random.randn(500) * 1000,
        'volume': 1000 + np.random.randn(500) * 100
    })
    df.set_index('timestamp', inplace=True)

    print(f"[OK] 데이터 생성: {len(df)} 캔들")

    # 2. BacktestOptimizer 생성
    base_optimizer = BacktestOptimizer(
        strategy_class=AlphaX7Core,
        df=df,
        strategy_type='macd'
    )
    print("[OK] BacktestOptimizer 생성")

    # 3. MetaOptimizer 생성 (작은 샘플, 1회 반복)
    meta = MetaOptimizer(
        base_optimizer=base_optimizer,
        sample_size=50,  # 작은 샘플 (빠른 테스트)
        max_iterations=1,  # 1회만 실행
        min_improvement=0.05
    )
    print("[OK] MetaOptimizer 생성")

    # 4. 메타 최적화 실행
    print("\n--- 메타 최적화 시작 (Phase 1 Coarse Grid만 실행) ---")
    try:
        result = meta.run_meta_optimization(
            df=df,
            trend_tf='1h',
            metric='sharpe_ratio'
        )

        # 5. 결과 검증
        print("\n=== 결과 검증 ===")

        # optimal_params 확인
        assert 'optimal_params' in result, "optimal_params 누락"
        optimal = result['optimal_params']
        print(f"\n[OK] optimal_params 존재: {len(optimal)} 파라미터")
        print(f"  - atr_mult: {optimal.get('atr_mult')}")
        print(f"  - filter_tf: {optimal.get('filter_tf')}")
        print(f"  - trail_start_r: {optimal.get('trail_start_r')}")
        print(f"  - trail_dist_r: {optimal.get('trail_dist_r')}")
        print(f"  - entry_validity_hours: {optimal.get('entry_validity_hours')}")

        # best_result 타임스탬프 확인
        assert 'best_result' in result, "best_result 누락"
        best = result['best_result']

        if best is not None:
            print(f"\n[OK] best_result 타임스탬프:")
            print(f"  - Start: {best.backtest_start_time}")
            print(f"  - End: {best.backtest_end_time}")
            print(f"  - Duration: {best.backtest_duration_days} days")

            # 타임스탬프 필드 검증
            assert hasattr(best, 'backtest_start_time'), "backtest_start_time 누락"
            assert hasattr(best, 'backtest_end_time'), "backtest_end_time 누락"
            assert hasattr(best, 'backtest_duration_days'), "backtest_duration_days 누락"

            # 기간이 양수인지 확인 (거래가 있을 경우)
            if best.trades > 0:
                assert best.backtest_duration_days >= 0, f"Duration 음수: {best.backtest_duration_days}"
        else:
            print("\n[WARN] best_result is None (거래 없음)")

        # 통계 확인
        stats = result['statistics']
        print(f"\n[OK] 통계:")
        print(f"  - 총 조합 수: {stats['total_combinations_tested']}")
        print(f"  - 실행 시간: {stats['time_elapsed_seconds']:.1f}초")

        print("\n[SUCCESS] 통합 테스트 통과!")

    except Exception as e:
        print(f"\n[FAIL] 메타 최적화 실패: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == '__main__':
    try:
        # 테스트 1: 타임스탬프 추출
        test_timestamp_extraction()

        # 테스트 2: OptimizationResult 필드
        test_optimization_result_with_timestamps()

        # 테스트 3: 통합 테스트 (시간 소요 - 스킵 가능)
        test_grid_meta_with_timestamps()

        print("\n" + "="*50)
        print("[SUCCESS] v7.22 통합 테스트 완료!")
        print("="*50)

    except Exception as e:
        print(f"\n[FAIL] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
