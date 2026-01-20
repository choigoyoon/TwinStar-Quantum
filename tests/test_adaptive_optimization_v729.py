"""
v7.29 Adaptive 최적화 테스트

물리 코어 + NumPy 스레드 고려 + Adaptive 샘플링 통합 테스트
"""
import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.optimizer import (
    get_numpy_threads,
    get_optimal_workers,
    get_worker_info,
    generate_adaptive_grid,
    generate_deep_grid,
    estimate_combinations
)


def test_numpy_thread_detection():
    """Test 1: NumPy 스레드 감지"""
    print("\n" + "="*60)
    print("Test 1: NumPy 스레드 감지")
    print("="*60)

    numpy_threads = get_numpy_threads()
    print(f"NumPy 스레드 수: {numpy_threads}")

    # 환경 변수 확인
    mkl = os.environ.get('MKL_NUM_THREADS', 'None')
    openblas = os.environ.get('OPENBLAS_NUM_THREADS', 'None')
    omp = os.environ.get('OMP_NUM_THREADS', 'None')

    print(f"MKL_NUM_THREADS: {mkl}")
    print(f"OPENBLAS_NUM_THREADS: {openblas}")
    print(f"OMP_NUM_THREADS: {omp}")

    assert numpy_threads >= 1, "NumPy 스레드는 최소 1개여야 합니다"
    print("✅ Test 1 통과")


def test_physical_core_detection():
    """Test 2: 물리 코어 감지 (psutil)"""
    print("\n" + "="*60)
    print("Test 2: 물리 코어 감지")
    print("="*60)

    try:
        import psutil
        physical = psutil.cpu_count(logical=False)
        logical = psutil.cpu_count(logical=True)

        print(f"물리 코어: {physical}개")
        print(f"논리 코어: {logical}개")
        print(f"하이퍼스레딩: {'Yes' if logical > physical else 'No'}")

        assert physical > 0, "물리 코어는 1개 이상이어야 합니다"
        assert logical >= physical, "논리 코어는 물리 코어보다 크거나 같아야 합니다"
        print("✅ Test 2 통과")
    except ImportError:
        print("⚠️ psutil 없음, 테스트 스킵")


def test_worker_allocation():
    """Test 3: 워커 배치 로직"""
    print("\n" + "="*60)
    print("Test 3: 워커 배치 로직 (모드별)")
    print("="*60)

    modes = ['quick', 'standard', 'deep']

    for mode in modes:
        workers = get_optimal_workers(mode)
        info = get_worker_info(mode)

        print(f"\n[{mode.upper()} 모드]")
        print(f"  물리 코어: {info.get('physical_cores', 'N/A')}개")
        print(f"  논리 코어: {info['total_cores']}개")
        print(f"  하이퍼스레딩: {info.get('hyperthreading', False)}")
        print(f"  NumPy 스레드: {info.get('numpy_threads', 1)}개")
        print(f"  워커 수: {info['workers']}개")
        print(f"  총 스레드: {info.get('total_threads', workers)}개")
        print(f"  CPU 사용률: {info['usage_percent']:.1f}%")
        print(f"  메모리 제약: {info['memory_limited']}")

        assert workers >= 1, f"{mode} 모드 워커는 최소 1개여야 합니다"
        assert workers <= info['total_cores'], f"{mode} 모드 워커는 논리 코어를 초과할 수 없습니다"

    print("\n✅ Test 3 통과")


def test_adaptive_grid():
    """Test 4: Adaptive 그리드 생성"""
    print("\n" + "="*60)
    print("Test 4: Adaptive 그리드 생성")
    print("="*60)

    # Deep 그리드 (전체)
    deep_grid = generate_deep_grid('1h')
    deep_total, deep_time = estimate_combinations(deep_grid)

    print(f"\n[Deep 모드 - 전수 조사]")
    print(f"  조합 수: {deep_total:,}개")
    print(f"  예상 시간: {deep_time:.1f}분")

    # Adaptive 그리드 (샘플링)
    adaptive_grid = generate_adaptive_grid('1h')
    adaptive_total, adaptive_time = estimate_combinations(adaptive_grid)

    print(f"\n[Adaptive 모드 - 계층 샘플링]")
    print(f"  조합 수: {adaptive_total:,}개")
    print(f"  예상 시간: {adaptive_time:.1f}분")

    # 비교
    reduction_ratio = (1 - adaptive_total / deep_total) * 100
    time_savings = (1 - adaptive_time / deep_time) * 100

    print(f"\n[개선 효과]")
    print(f"  조합 감소: -{reduction_ratio:.1f}%")
    print(f"  시간 절약: -{time_savings:.1f}%")
    print(f"  핵심 파라미터 검사율:")
    print(f"    - atr_mult: 100% ({len(adaptive_grid['atr_mult'])}/{len(deep_grid['atr_mult'])})")
    print(f"    - filter_tf: 100% ({len(adaptive_grid['filter_tf'])}/{len(deep_grid['filter_tf'])})")
    print(f"    - trail_start_r: 50% ({len(adaptive_grid['trail_start_r'])}/{len(deep_grid['trail_start_r'])})")
    print(f"    - trail_dist_r: 50% ({len(adaptive_grid['trail_dist_r'])}/{len(deep_grid['trail_dist_r'])})")
    print(f"    - entry_validity_hours: 29% ({len(adaptive_grid['entry_validity_hours'])}/{len(deep_grid['entry_validity_hours'])})")

    # 검증
    assert adaptive_total < deep_total, "Adaptive 조합 수가 Deep보다 적어야 합니다"
    assert adaptive_total == 360, f"Adaptive 조합 수는 360개여야 합니다 (실제: {adaptive_total})"
    assert reduction_ratio > 60, f"최소 60% 감소해야 합니다 (실제: {reduction_ratio:.1f}%)"

    # 핵심 파라미터 100% 검사 확인
    assert len(adaptive_grid['atr_mult']) == len(deep_grid['atr_mult']), "atr_mult는 100% 검사해야 합니다"
    assert len(adaptive_grid['filter_tf']) == len(deep_grid['filter_tf']), "filter_tf는 100% 검사해야 합니다"

    print("\n✅ Test 4 통과")


def test_memory_constraint():
    """Test 5: 메모리 제약 시뮬레이션"""
    print("\n" + "="*60)
    print("Test 5: 메모리 제약 시뮬레이션")
    print("="*60)

    # 저사양 PC 시나리오 (2GB RAM)
    workers_low = get_optimal_workers('deep', available_memory_gb=1.5)
    print(f"\n[저사양 PC: 1.5GB RAM]")
    print(f"  Deep 모드 워커: {workers_low}개")
    assert workers_low <= 2, "1.5GB RAM에서는 최대 2개 워커"

    # 표준 PC 시나리오 (6GB RAM)
    workers_mid = get_optimal_workers('deep', available_memory_gb=6.0)
    print(f"\n[표준 PC: 6GB RAM]")
    print(f"  Deep 모드 워커: {workers_mid}개")
    assert workers_mid <= 6, "6GB RAM에서는 최대 6개 워커"

    # 고사양 PC 시나리오 (16GB RAM)
    workers_high = get_optimal_workers('deep', available_memory_gb=16.0)
    print(f"\n[고사양 PC: 16GB RAM]")
    print(f"  Deep 모드 워커: {workers_high}개")

    print("\n✅ Test 5 통과")


def test_performance_comparison():
    """Test 6: 성능 비교 (8코어 16스레드 기준)"""
    print("\n" + "="*60)
    print("Test 6: 성능 비교 (8코어 16스레드 시뮬레이션)")
    print("="*60)

    # 시뮬레이션: 8코어 16스레드 PC
    print("\n[시나리오: Ryzen 7 5800X (8코어 16스레드)]")

    # Deep 모드 (전수 조사)
    deep_grid = generate_deep_grid('1h')
    deep_total, _ = estimate_combinations(deep_grid)

    # NumPy 단일 스레드 가정
    numpy_threads = 1
    workers_deep = 10  # 물리 8 + 논리 2 (8 + 8//3)
    time_per_combo = 15  # 초
    deep_time_sec = deep_total * time_per_combo / workers_deep / 60  # 분

    print(f"\n[Deep 모드 - 전수 조사]")
    print(f"  조합: {deep_total:,}개")
    print(f"  워커: {workers_deep}개 (물리 8 + 논리 2)")
    print(f"  NumPy 스레드: {numpy_threads}개")
    print(f"  총 CPU 스레드: {workers_deep * numpy_threads}개")
    print(f"  예상 시간: {deep_time_sec:.1f}분")

    # Adaptive 모드 (샘플링)
    adaptive_grid = generate_adaptive_grid('1h')
    adaptive_total, _ = estimate_combinations(adaptive_grid)
    adaptive_time_sec = adaptive_total * time_per_combo / workers_deep / 60  # 분

    print(f"\n[Adaptive 모드 - 계층 샘플링]")
    print(f"  조합: {adaptive_total:,}개")
    print(f"  워커: {workers_deep}개 (동일)")
    print(f"  NumPy 스레드: {numpy_threads}개")
    print(f"  총 CPU 스레드: {workers_deep * numpy_threads}개")
    print(f"  예상 시간: {adaptive_time_sec:.1f}분")

    # 개선율
    time_reduction = (1 - adaptive_time_sec / deep_time_sec) * 100

    print(f"\n[개선 효과]")
    print(f"  실행 시간: {deep_time_sec:.1f}분 → {adaptive_time_sec:.1f}분 (-{time_reduction:.1f}%)")
    print(f"  핵심 파라미터 보장: atr_mult 100%, filter_tf 100%")

    assert time_reduction > 60, f"최소 60% 시간 절약 필요 (실제: {time_reduction:.1f}%)"

    print("\n✅ Test 6 통과")


if __name__ == '__main__':
    print("="*60)
    print("v7.29 Adaptive 최적화 테스트 시작")
    print("="*60)

    try:
        test_numpy_thread_detection()
        test_physical_core_detection()
        test_worker_allocation()
        test_adaptive_grid()
        test_memory_constraint()
        test_performance_comparison()

        print("\n" + "="*60)
        print("✅ 전체 테스트 통과 (6/6)")
        print("="*60)

    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
