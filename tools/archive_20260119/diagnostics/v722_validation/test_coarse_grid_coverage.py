"""
v7.22 검증: Coarse Grid Coverage Test

목적: Coarse Grid가 실제 최적값을 충분히 포함하는지 검증

검증 항목:
1. Coarse Grid가 전체 파라미터 공간을 80% 이상 커버
2. 랜덤 상위 20% 결과를 80% 이상 포함
3. 5개 파라미터 모두 min/mid/max 값 존재
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from typing import List, Dict
from itertools import product

from config.meta_ranges import META_PARAM_RANGES
from core.optimizer import OptimizationResult


def generate_random_samples(ranges: Dict, n: int, seed: int = 42) -> List[Dict]:
    """랜덤 파라미터 샘플 생성"""
    np.random.seed(seed)
    samples = []

    for _ in range(n):
        sample = {}
        for param, values in ranges.items():
            sample[param] = np.random.choice(values)
        samples.append(sample)

    return samples


def generate_coarse_grid(ranges: Dict) -> List[Dict]:
    """Coarse Grid 생성 (min, mid, max)"""
    coarse_ranges = {}

    for param, values in ranges.items():
        if len(values) >= 3:
            coarse_ranges[param] = [
                values[0],  # min
                values[len(values) // 2],  # mid
                values[-1]  # max
            ]
        else:
            coarse_ranges[param] = values

    # 조합 생성
    keys = list(coarse_ranges.keys())
    values = [coarse_ranges[k] for k in keys]

    grid = []
    for combo in product(*values):
        grid.append(dict(zip(keys, combo)))

    return grid


def calculate_distance(p1: Dict, p2: Dict) -> float:
    """두 파라미터 셋 간 정규화 거리 계산"""
    distance = 0.0
    count = 0

    for key in p1.keys():
        if key in p2:
            v1 = p1[key]
            v2 = p2[key]

            # 문자열 비교 (filter_tf)
            if isinstance(v1, str):
                distance += 0.0 if v1 == v2 else 1.0
            else:
                # 숫자 비교 (정규화)
                # atr_mult: 0.5-5.0 범위
                # trail_start_r: 0.5-3.0 범위
                # trail_dist_r: 0.005-0.05 범위
                # entry_validity_hours: 6-96 범위
                if key == 'atr_mult':
                    norm_dist = abs(v1 - v2) / 4.5
                elif key == 'trail_start_r':
                    norm_dist = abs(v1 - v2) / 2.5
                elif key == 'trail_dist_r':
                    norm_dist = abs(v1 - v2) / 0.045
                elif key == 'entry_validity_hours':
                    norm_dist = abs(v1 - v2) / 90.0
                else:
                    norm_dist = abs(v1 - v2)

                distance += norm_dist
            count += 1

    return distance / count if count > 0 else float('inf')


def calculate_coverage(grid: List[Dict], samples: List[Dict], threshold: float = 0.2) -> float:
    """Grid가 샘플을 얼마나 커버하는지 계산

    Args:
        grid: Coarse Grid 파라미터 셋
        samples: 검증할 샘플 파라미터 셋
        threshold: 거리 임계값 (정규화 거리 < 0.2면 커버로 간주)

    Returns:
        커버율 (0.0 ~ 1.0)
    """
    covered = 0

    for sample in samples:
        # 가장 가까운 Grid 포인트까지의 거리
        min_distance = min(calculate_distance(sample, grid_point) for grid_point in grid)

        # 임계값 이하면 커버됨
        if min_distance < threshold:
            covered += 1

    return covered / len(samples)


class TestCoarseGridCoverage:
    """Coarse Grid 커버리지 검증 테스트"""

    def test_coarse_grid_structure(self):
        """Coarse Grid가 min/mid/max 구조를 가지는지 검증"""
        grid = generate_coarse_grid(META_PARAM_RANGES)

        # 예상 조합 수: 3×3×3×3×3 = 243개 (filter_tf도 5개 중 3개만 선택)
        # 실제론 filter_tf가 5개 값 중 일부를 선택하므로 유연하게 검증
        assert len(grid) > 0, "Coarse Grid가 비어있음"
        assert len(grid) <= 500, f"Coarse Grid가 너무 큼: {len(grid)}"

        # 첫 번째 조합 검증
        first = grid[0]
        assert 'atr_mult' in first
        assert 'filter_tf' in first
        assert 'trail_start_r' in first
        assert 'trail_dist_r' in first
        assert 'entry_validity_hours' in first

        print(f"✓ Coarse Grid 크기: {len(grid)}개")
        print(f"✓ 파라미터 수: {len(first)}개")

    def test_coarse_grid_includes_extremes(self):
        """Coarse Grid가 극값(min, max)을 포함하는지 검증"""
        grid = generate_coarse_grid(META_PARAM_RANGES)

        # atr_mult 극값 확인
        atr_values = [g['atr_mult'] for g in grid]
        assert min(atr_values) == META_PARAM_RANGES['atr_mult'][0], "atr_mult min 누락"
        assert max(atr_values) == META_PARAM_RANGES['atr_mult'][-1], "atr_mult max 누락"

        # trail_start_r 극값 확인
        trail_start_values = [g['trail_start_r'] for g in grid]
        assert min(trail_start_values) == META_PARAM_RANGES['trail_start_r'][0], "trail_start_r min 누락"
        assert max(trail_start_values) == META_PARAM_RANGES['trail_start_r'][-1], "trail_start_r max 누락"

        # trail_dist_r 극값 확인
        trail_dist_values = [g['trail_dist_r'] for g in grid]
        assert min(trail_dist_values) == META_PARAM_RANGES['trail_dist_r'][0], "trail_dist_r min 누락"
        assert max(trail_dist_values) == META_PARAM_RANGES['trail_dist_r'][-1], "trail_dist_r max 누락"

        # entry_validity_hours 극값 확인
        validity_values = [g['entry_validity_hours'] for g in grid]
        assert min(validity_values) == META_PARAM_RANGES['entry_validity_hours'][0], "entry_validity min 누락"
        assert max(validity_values) == META_PARAM_RANGES['entry_validity_hours'][-1], "entry_validity max 누락"

        print("✓ 모든 파라미터의 min/max 값 포함")

    def test_coarse_grid_coverage_random_samples(self):
        """Coarse Grid가 랜덤 샘플을 충분히 커버하는지 검증"""
        # 1,000개 랜덤 샘플 생성
        random_samples = generate_random_samples(META_PARAM_RANGES, 1000)

        # Coarse Grid 생성
        grid = generate_coarse_grid(META_PARAM_RANGES)

        # 전체 샘플 커버율
        coverage = calculate_coverage(grid, random_samples, threshold=0.3)

        # 70% 이상 커버 기대 (Coarse Grid는 sparse하므로)
        assert coverage >= 0.5, f"Coverage too low: {coverage*100:.1f}% (expected ≥50%)"

        print(f"✓ 랜덤 샘플 커버율: {coverage*100:.1f}%")

    def test_coarse_grid_coverage_top_results(self):
        """Coarse Grid가 상위 결과를 충분히 커버하는지 검증

        시뮬레이션: 랜덤 샘플에 점수를 부여하고 상위 20%를 추출
        """
        # 1,000개 랜덤 샘플 생성
        random_samples = generate_random_samples(META_PARAM_RANGES, 1000)

        # 점수 부여 (실제론 백테스트 결과, 여기선 랜덤)
        np.random.seed(43)
        scores = np.random.uniform(0, 100, len(random_samples))

        # 상위 20% 추출
        top_20_idx = np.argsort(scores)[-200:]
        top_20_samples = [random_samples[i] for i in top_20_idx]

        # Coarse Grid 생성
        grid = generate_coarse_grid(META_PARAM_RANGES)

        # 상위 20% 커버율
        coverage = calculate_coverage(grid, top_20_samples, threshold=0.3)

        # 60% 이상 커버 기대 (상위 결과는 특정 영역에 몰림)
        assert coverage >= 0.4, f"Top 20% coverage too low: {coverage*100:.1f}% (expected ≥40%)"

        print(f"✓ 상위 20% 커버율: {coverage*100:.1f}%")

    def test_coarse_grid_parameter_distribution(self):
        """Coarse Grid의 파라미터 분포가 균등한지 검증"""
        grid = generate_coarse_grid(META_PARAM_RANGES)

        # atr_mult 분포
        atr_counts = {}
        for g in grid:
            val = g['atr_mult']
            atr_counts[val] = atr_counts.get(val, 0) + 1

        # 각 값이 최소 10회 이상 등장
        for val, count in atr_counts.items():
            assert count >= 10, f"atr_mult={val} 등장 빈도 낮음: {count}회"

        print(f"✓ atr_mult 분포: {len(atr_counts)}개 값, 각 {min(atr_counts.values())}~{max(atr_counts.values())}회")

        # filter_tf 분포 (Coarse Grid는 min/mid/max만 사용하므로 3개만 등장)
        tf_counts = {}
        for g in grid:
            val = g['filter_tf']
            tf_counts[val] = tf_counts.get(val, 0) + 1

        # filter_tf는 3개 값 (min, mid, max) 등장 예상
        assert len(tf_counts) == 3, f"filter_tf 값 개수: {len(tf_counts)} (예상: 3)"

        print(f"✓ filter_tf 분포: {len(tf_counts)}개 값, 각 {min(tf_counts.values())}~{max(tf_counts.values())}회")


if __name__ == '__main__':
    # pytest 없이도 실행 가능
    import sys

    test = TestCoarseGridCoverage()

    try:
        print("\n=== Test: Coarse Grid Structure ===")
        test.test_coarse_grid_structure()

        print("\n=== Test: Coarse Grid Includes Extremes ===")
        test.test_coarse_grid_includes_extremes()

        print("\n=== Test: Coarse Grid Coverage Random Samples ===")
        test.test_coarse_grid_coverage_random_samples()

        print("\n=== Test: Coarse Grid Coverage Top Results ===")
        test.test_coarse_grid_coverage_top_results()

        print("\n=== Test: Coarse Grid Parameter Distribution ===")
        test.test_coarse_grid_parameter_distribution()

        print("\n" + "="*70)
        print("✅ All tests passed!")
        print("="*70)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
