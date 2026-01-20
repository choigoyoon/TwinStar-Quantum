"""적응형 범위 생성기 단위 테스트 - v7.25.2

2단계 Coarse-to-Fine 범위 생성 테스트

Author: Claude Sonnet 4.5
Date: 2026-01-18
"""

import sys
from pathlib import Path

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.adaptive_range_builder import (
    build_coarse_ranges,
    build_fine_ranges
)


def test_coarse_ranges():
    """Coarse Grid 범위 검증 (324개 조합)"""
    ranges = build_coarse_ranges()

    # 1. 필수 키 검증
    assert 'atr_mult' in ranges
    assert 'filter_tf' in ranges
    assert 'entry_validity_hours' in ranges
    assert 'trail_start_r' in ranges
    assert 'trail_dist_r' in ranges

    # 2. 개수 검증
    assert len(ranges['atr_mult']) == 4, f"Expected 4 atr_mult, got {len(ranges['atr_mult'])}"
    assert len(ranges['filter_tf']) == 3, f"Expected 3 filter_tf, got {len(ranges['filter_tf'])}"
    assert len(ranges['entry_validity_hours']) == 3, f"Expected 3 entry_validity_hours, got {len(ranges['entry_validity_hours'])}"
    assert len(ranges['trail_start_r']) == 3, f"Expected 3 trail_start_r, got {len(ranges['trail_start_r'])}"
    assert len(ranges['trail_dist_r']) == 3, f"Expected 3 trail_dist_r, got {len(ranges['trail_dist_r'])}"

    # 3. 총 조합 수 검증 (4×3×3×3×3 = 324)
    total = 1
    for values in ranges.values():
        total *= len(values)
    assert total == 324, f"Expected 324 combinations, got {total}"

    # 4. 값 검증
    assert ranges['atr_mult'] == [0.5, 1.0, 1.5, 2.0]
    assert ranges['filter_tf'] == ['2h', '4h', '12h']
    assert ranges['entry_validity_hours'] == [12, 48, 96]
    assert ranges['trail_start_r'] == [0.3, 0.6, 1.0]
    assert ranges['trail_dist_r'] == [0.02, 0.05, 0.10]

    print("✅ test_coarse_ranges 통과 (324개 조합)")


def test_fine_ranges_atr():
    """ATR Fine 범위 검증 (±20%)"""
    coarse_optimal = {
        'atr_mult': 1.0,
        'filter_tf': '4h',
        'entry_validity_hours': 48,
        'trail_start_r': 0.6,
        'trail_dist_r': 0.05
    }

    ranges = build_fine_ranges(coarse_optimal)

    # 1. ATR ±20% 범위 검증
    atr_values = ranges['atr_mult']
    assert len(atr_values) == 5, f"Expected 5 atr_mult values, got {len(atr_values)}"

    # 최소값: max(0.3, 1.0 * 0.8) = 0.8
    # 최대값: min(3.0, 1.0 * 1.2) = 1.2
    assert atr_values[0] == 0.8, f"Expected min 0.8, got {atr_values[0]}"
    assert atr_values[2] == 1.0, f"Expected center 1.0, got {atr_values[2]}"
    assert atr_values[4] == 1.2, f"Expected max 1.2, got {atr_values[4]}"

    print("✅ test_fine_ranges_atr 통과 (±20% 범위)")


def test_fine_ranges_filter_tf():
    """filter_tf Fine 범위 검증 (전후 1단계)"""
    coarse_optimal = {
        'atr_mult': 1.0,
        'filter_tf': '4h',
        'entry_validity_hours': 48,
        'trail_start_r': 0.6,
        'trail_dist_r': 0.05
    }

    ranges = build_fine_ranges(coarse_optimal)

    # filter_tf 전후 1단계 검증
    # '4h' → ['3h', '4h', '6h']
    assert '3h' in ranges['filter_tf'], "Should include previous step (3h)"
    assert '4h' in ranges['filter_tf'], "Should include center (4h)"
    assert '6h' in ranges['filter_tf'], "Should include next step (6h)"

    print("✅ test_fine_ranges_filter_tf 통과 (전후 1단계)")


def test_fine_ranges_edge_cases():
    """Fine 범위 경계값 검증"""
    # Edge case 1: ATR 최소값 (0.3)
    coarse_optimal = {
        'atr_mult': 0.3,
        'filter_tf': '1h',
        'entry_validity_hours': 12,
        'trail_start_r': 0.3,
        'trail_dist_r': 0.02
    }

    ranges = build_fine_ranges(coarse_optimal)

    # ATR 최소값 유지 (0.3 * 0.8 = 0.24 → max(0.3, 0.24) = 0.3)
    assert ranges['atr_mult'][0] >= 0.3, f"ATR min should be >= 0.3, got {ranges['atr_mult'][0]}"

    # filter_tf 경계값 (이전 단계 없음)
    assert '1h' in ranges['filter_tf'], "Should include 1h even at edge"

    # Edge case 2: ATR 최대값 (3.0)
    coarse_optimal['atr_mult'] = 2.6
    ranges = build_fine_ranges(coarse_optimal)

    # ATR 최대값 제한 (2.6 * 1.2 = 3.12 → min(3.0, 3.12) = 3.0)
    assert ranges['atr_mult'][-1] <= 3.0, f"ATR max should be <= 3.0, got {ranges['atr_mult'][-1]}"

    print("✅ test_fine_ranges_edge_cases 통과 (경계값 처리)")


def test_combination_count():
    """총 조합 수 검증"""
    # Stage 1: Coarse
    coarse_ranges = build_coarse_ranges()
    coarse_total = 1
    for values in coarse_ranges.values():
        coarse_total *= len(values)

    assert coarse_total == 324, f"Expected 324 coarse combos, got {coarse_total}"

    # Stage 2: Fine (하나의 영역)
    coarse_optimal = {
        'atr_mult': 1.0,
        'filter_tf': '4h',
        'entry_validity_hours': 48,
        'trail_start_r': 0.6,
        'trail_dist_r': 0.05
    }

    fine_ranges = build_fine_ranges(coarse_optimal)
    fine_total = 1
    for values in fine_ranges.values():
        fine_total *= len(values)

    # Fine: 5×3×5×5×5 = 1,875 (이론값)
    # 실제로는 filter_tf가 3개이므로 5×3×5×5×5 = 1,875
    assert 100 <= fine_total <= 2000, f"Expected ~1875 fine combos per region, got {fine_total}"

    # 전체 이론값: 324 (Stage 1) + 1,875×5 (Stage 2, 5개 영역) = 324 + 9,375 = 9,699
    # 실제 실행 시 중복 제거 및 영역별 차이로 ~824개 예상
    # 하지만 여기서는 이론값만 검증
    print(f"✅ test_combination_count 통과 (Coarse: {coarse_total}, Fine: {fine_total}/영역)")


if __name__ == '__main__':
    # UTF-8 출력 설정 (Windows)
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 80)
    print("🧪 적응형 범위 생성기 단위 테스트 - v7.25.2")
    print("=" * 80)

    try:
        test_coarse_ranges()
        test_fine_ranges_atr()
        test_fine_ranges_filter_tf()
        test_fine_ranges_edge_cases()
        test_combination_count()

        print("\n" + "=" * 80)
        print("✅ 모든 테스트 통과! (5/5)")
        print("=" * 80)

    except AssertionError as e:
        print(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
