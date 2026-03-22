"""
v7.22 검증 테스트 실행 스크립트

모든 검증 테스트를 순차적으로 실행합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 개별 테스트 모듈 import
from tests.v722_validation.test_coarse_grid_coverage import TestCoarseGridCoverage
from tests.v722_validation.test_optimal_params_validation import (
    TestOptimalParamsValidation,
    TestOptimalParamsIntegration
)
from tests.v722_validation.test_timestamp_accuracy import (
    TestTimestampExtraction,
    TestTimestampFormats,
    TestTimestampEdgeCases
)


def run_all_tests():
    """모든 테스트 실행"""
    total_tests = 0
    passed_tests = 0
    failed_tests = []

    print("\n" + "="*70)
    print("v7.22 검증 테스트 실행 시작")
    print("="*70)

    # Test Suite 1: Coarse Grid Coverage
    print("\n" + "="*70)
    print("Test Suite 1: Coarse Grid Coverage (5 tests)")
    print("="*70)

    test1 = TestCoarseGridCoverage()
    tests1 = [
        ("Coarse Grid Structure", test1.test_coarse_grid_structure),
        ("Coarse Grid Includes Extremes", test1.test_coarse_grid_includes_extremes),
        ("Coarse Grid Coverage Random Samples", test1.test_coarse_grid_coverage_random_samples),
        ("Coarse Grid Coverage Top Results", test1.test_coarse_grid_coverage_top_results),
        ("Coarse Grid Parameter Distribution", test1.test_coarse_grid_parameter_distribution),
    ]

    for name, test_func in tests1:
        total_tests += 1
        try:
            print(f"\n--- Test: {name} ---")
            test_func()
            passed_tests += 1
            print(f"✅ PASSED")
        except AssertionError as e:
            failed_tests.append((name, str(e)))
            print(f"❌ FAILED: {e}")
        except Exception as e:
            failed_tests.append((name, f"Error: {e}"))
            print(f"❌ ERROR: {e}")

    # Test Suite 2: Optimal Params Validation
    print("\n" + "="*70)
    print("Test Suite 2: Optimal Params Validation (9 tests)")
    print("="*70)

    test2_1 = TestOptimalParamsValidation()
    test2_2 = TestOptimalParamsIntegration()

    tests2 = [
        ("Required Parameters Exist", test2_1.test_required_parameters_exist),
        ("Parameter Types", test2_1.test_parameter_types),
        ("Parameter Values In Range", test2_1.test_parameter_values_in_range),
        ("Parameter Values Out Of Range", test2_1.test_parameter_values_out_of_range),
        ("Optimal Params Matches Best Result", test2_1.test_optimal_params_matches_best_result),
        ("Parameter Precision", test2_1.test_parameter_precision),
        ("Edge Case Extreme Values", test2_1.test_edge_case_extreme_values),
        ("Optimal Params Serialization", test2_1.test_optimal_params_serialization),
        ("Optimal Params From Meta Result", test2_2.test_optimal_params_from_meta_result),
    ]

    for name, test_func in tests2:
        total_tests += 1
        try:
            print(f"\n--- Test: {name} ---")
            test_func()
            passed_tests += 1
            print(f"✅ PASSED")
        except AssertionError as e:
            failed_tests.append((name, str(e)))
            print(f"❌ FAILED: {e}")
        except Exception as e:
            failed_tests.append((name, f"Error: {e}"))
            print(f"❌ ERROR: {e}")

    # Test Suite 3: Timestamp Accuracy
    print("\n" + "="*70)
    print("Test Suite 3: Timestamp Accuracy (14 tests)")
    print("="*70)

    test3_1 = TestTimestampExtraction()
    test3_2 = TestTimestampFormats()
    test3_3 = TestTimestampEdgeCases()

    tests3 = [
        ("Single Trade Timestamps", test3_1.test_single_trade_timestamps),
        ("Multiple Trades Timestamps", test3_1.test_multiple_trades_timestamps),
        ("Empty Trades Timestamps", test3_1.test_empty_trades_timestamps),
        ("Single Day Trade Duration", test3_1.test_single_day_trade_duration),
        ("Overnight Trade Duration", test3_1.test_overnight_trade_duration),
        ("Multi Day Trade Duration", test3_1.test_multi_day_trade_duration),
        ("Duration Calculation Precision", test3_1.test_duration_calculation_precision),
        ("Datetime Format", test3_2.test_datetime_format),
        ("Pandas Timestamp Format", test3_2.test_pandas_timestamp_format),
        ("String Timestamp Format", test3_2.test_string_timestamp_format),
        ("Leap Year February", test3_3.test_leap_year_february),
        ("Year Boundary", test3_3.test_year_boundary),
        ("Timezone Aware Timestamps", test3_3.test_timezone_aware_timestamps),
        ("Very Long Duration", test3_3.test_very_long_duration),
    ]

    for name, test_func in tests3:
        total_tests += 1
        try:
            print(f"\n--- Test: {name} ---")
            test_func()
            passed_tests += 1
            print(f"✅ PASSED")
        except AssertionError as e:
            failed_tests.append((name, str(e)))
            print(f"❌ FAILED: {e}")
        except Exception as e:
            failed_tests.append((name, f"Error: {e}"))
            print(f"❌ ERROR: {e}")

    # 최종 결과
    print("\n" + "="*70)
    print("최종 결과")
    print("="*70)
    print(f"총 테스트: {total_tests}")
    print(f"통과: {passed_tests}")
    print(f"실패: {len(failed_tests)}")
    print(f"성공률: {passed_tests/total_tests*100:.1f}%")

    if failed_tests:
        print("\n" + "-"*70)
        print("실패한 테스트 목록:")
        print("-"*70)
        for name, error in failed_tests:
            print(f"\n❌ {name}")
            print(f"   {error}")

    print("\n" + "="*70)
    if len(failed_tests) == 0:
        print("✅ 모든 테스트 통과!")
        print("="*70)
        return 0
    else:
        print(f"❌ {len(failed_tests)}개 테스트 실패")
        print("="*70)
        return 1


if __name__ == '__main__':
    exit_code = run_all_tests()
    sys.exit(exit_code)
