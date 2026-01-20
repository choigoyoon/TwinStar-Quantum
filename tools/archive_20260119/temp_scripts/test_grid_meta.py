"""그리드 기반 Meta 최적화 테스트

새로 구현한 3단계 적응형 그리드 탐색을 검증합니다.
"""

import pandas as pd
import numpy as np
from core.meta_optimizer import MetaOptimizer
from core.optimizer import BacktestOptimizer
from core.strategy_core import AlphaX7Core


def test_grid_meta_basic():
    """기본 그리드 Meta 테스트"""
    print("=== 그리드 Meta 기본 테스트 ===\n")

    # 1. 더미 데이터 생성 (1,000개 캔들)
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=1000, freq='15min')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 50000 + np.random.randn(1000) * 1000,
        'high': 50100 + np.random.randn(1000) * 1000,
        'low': 49900 + np.random.randn(1000) * 1000,
        'close': 50000 + np.random.randn(1000) * 1000,
        'volume': 1000 + np.random.randn(1000) * 100
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

    # 3. MetaOptimizer 생성 (빠른 테스트: 최대 2회 반복)
    meta = MetaOptimizer(
        base_optimizer=base_optimizer,
        sample_size=100,  # 작은 샘플 (빠른 테스트)
        max_iterations=2,
        min_improvement=0.05
    )
    print("[OK] MetaOptimizer 생성")

    # 4. 메타 최적화 실행
    print("\n--- 메타 최적화 시작 ---")
    result = meta.run_meta_optimization(
        df=df,
        trend_tf='1h',
        metric='sharpe_ratio'
    )

    # 5. 결과 검증
    print("\n=== 결과 검증 ===")

    # optimal_params 존재 확인
    assert 'optimal_params' in result, "optimal_params 누락"
    optimal = result['optimal_params']
    print(f"[OK] optimal_params 존재: {len(optimal)} 파라미터")

    # 필수 파라미터 확인
    required_params = ['atr_mult', 'filter_tf', 'trail_start_r', 'trail_dist_r', 'entry_validity_hours']
    for param in required_params:
        assert param in optimal, f"{param} 누락"
        print(f"  - {param}: {optimal[param]}")

    # confidence_intervals 존재 확인
    assert 'confidence_intervals' in result, "confidence_intervals 누락"
    intervals = result['confidence_intervals']
    print(f"\n[OK] confidence_intervals 존재: {len(intervals)} 파라미터")

    # extracted_ranges (레거시 호환) 확인
    assert 'extracted_ranges' in result, "extracted_ranges 누락"
    ranges = result['extracted_ranges']
    print(f"\n[OK] extracted_ranges 존재: {len(ranges)} 파라미터")

    # 모드별 범위 확인
    for param in required_params:
        assert param in ranges, f"{param} 범위 누락"
        assert 'quick' in ranges[param], f"{param} quick 모드 누락"
        assert 'standard' in ranges[param], f"{param} standard 모드 누락"
        assert 'deep' in ranges[param], f"{param} deep 모드 누락"
        print(f"  - {param}: quick={len(ranges[param]['quick'])}, standard={len(ranges[param]['standard'])}, deep={len(ranges[param]['deep'])}")

    # 통계 확인
    stats = result['statistics']
    print(f"\n[OK] 통계:")
    print(f"  - 총 조합 수: {stats['total_combinations_tested']}")
    print(f"  - 실행 시간: {stats['time_elapsed_seconds']:.1f}초")
    print(f"  - 반복 횟수: {stats['convergence_iterations']}")
    print(f"  - 점수 이력: {stats['top_score_history']}")

    # 최고 점수 개선 확인
    scores = stats['top_score_history']
    if len(scores) >= 2:
        improvement = (scores[-1] - scores[0]) / scores[0] * 100
        print(f"  - 개선율: {improvement:.1f}%")

    print("\n[SUCCESS] 모든 테스트 통과!")


def test_coarse_grid_generation():
    """Coarse Grid 생성 테스트"""
    print("\n=== Coarse Grid 생성 테스트 ===\n")

    from config.meta_ranges import load_meta_param_ranges

    # MetaOptimizer 생성 (백테스트 없이)
    meta_ranges = load_meta_param_ranges()
    meta = MetaOptimizer(
        base_optimizer=None,  # 그리드 생성만 테스트
        meta_ranges=meta_ranges
    )

    # Coarse Grid 생성
    coarse_grid = meta._generate_coarse_grid()

    print("Coarse Grid 결과:")
    for param, values in coarse_grid.items():
        print(f"  {param}: {values} ({len(values)}개)")

    # 조합 수 계산
    total_combos = np.prod([len(v) for v in coarse_grid.values()])
    print(f"\n총 조합 수: {total_combos}")

    # 예상: 3^5 = 243개
    assert total_combos <= 300, f"Coarse Grid가 너무 큼: {total_combos}"
    print("[OK] Coarse Grid 크기 적합")


def test_refine_grid():
    """Grid Refinement 테스트"""
    print("\n=== Grid Refinement 테스트 ===\n")

    from core.optimizer import OptimizationResult
    from config.meta_ranges import load_meta_param_ranges

    # 더미 결과 생성
    dummy_results = []
    for i in range(100):
        result = OptimizationResult(
            params={
                'atr_mult': 1.5 + np.random.randn() * 0.3,
                'filter_tf': np.random.choice(['4h', '6h', '12h']),
                'trail_start_r': 1.0 + np.random.randn() * 0.2,
                'trail_dist_r': 0.02 + np.random.randn() * 0.005,
                'entry_validity_hours': 24.0 + np.random.randn() * 12.0
            },
            trades=100,
            win_rate=0.8,
            total_return=100.0,
            simple_return=100.0,
            compound_return=100.0,
            max_drawdown=0.1,
            sharpe_ratio=2.0 + np.random.randn() * 0.5,
            profit_factor=3.0
        )
        dummy_results.append(result)

    # Sharpe Ratio 기준 정렬
    dummy_results.sort(key=lambda r: r.sharpe_ratio, reverse=True)

    # MetaOptimizer 생성
    meta_ranges = load_meta_param_ranges()
    meta = MetaOptimizer(
        base_optimizer=None,
        meta_ranges=meta_ranges
    )

    # Fine Grid 생성 (5 points, ±50%)
    fine_grid = meta._refine_grid(dummy_results, n_points=5, range_factor=0.5)

    print("Fine Grid 결과:")
    for param, values in fine_grid.items():
        print(f"  {param}: {values} ({len(values)}개)")

    # Ultra-Fine Grid 생성 (7 points, ±20%)
    ultra_grid = meta._refine_grid(dummy_results, n_points=7, range_factor=0.2)

    print("\nUltra-Fine Grid 결과:")
    for param, values in ultra_grid.items():
        print(f"  {param}: {values} ({len(values)}개)")

    print("\n[OK] Grid Refinement 성공")


if __name__ == '__main__':
    try:
        # 테스트 1: Coarse Grid 생성
        test_coarse_grid_generation()

        # 테스트 2: Grid Refinement
        test_refine_grid()

        # 테스트 3: 전체 워크플로우 (시간 소요 - 스킵 가능)
        # test_grid_meta_basic()

        print("\n" + "="*50)
        print("[SUCCESS] 모든 테스트 통과!")
        print("="*50)

    except Exception as e:
        print(f"\n[FAIL] 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
