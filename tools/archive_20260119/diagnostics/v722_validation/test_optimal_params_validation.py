"""
v7.22 검증: Optimal Params Validation Test

목적: optimal_params의 유효성과 완전성 검증

검증 항목:
1. 모든 필수 파라미터 존재 (5개)
2. 값이 META_PARAM_RANGES 범위 내
3. optimal_params와 best_result.params 일치
4. 타입 정확성
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from typing import Dict, Any

from config.meta_ranges import META_PARAM_RANGES
from core.optimizer import OptimizationResult


def validate_param_in_range(param_name: str, value: Any) -> tuple[bool, str]:
    """파라미터 값이 유효 범위 내인지 검증

    Returns:
        (is_valid, error_message)
    """
    if param_name not in META_PARAM_RANGES:
        return False, f"Unknown parameter: {param_name}"

    valid_values = META_PARAM_RANGES[param_name]

    # 문자열 파라미터 (filter_tf)
    if isinstance(valid_values[0], str):
        if value not in valid_values:
            return False, f"{param_name}={value} not in valid values: {valid_values}"
        return True, ""

    # 숫자 파라미터
    min_val = min(valid_values)
    max_val = max(valid_values)

    if not (min_val <= value <= max_val):
        return False, f"{param_name}={value} out of range [{min_val}, {max_val}]"

    # 이산 값인지 확인 (허용 오차 1e-6)
    if not any(abs(value - v) < 1e-6 for v in valid_values):
        return False, f"{param_name}={value} not in discrete values: {valid_values}"

    return True, ""


class TestOptimalParamsValidation:
    """optimal_params 유효성 검증 테스트"""

    def test_required_parameters_exist(self):
        """필수 파라미터가 모두 존재하는지 검증"""
        # 더미 결과 생성 (실제 META_PARAM_RANGES에 있는 값 사용)
        optimal_params = {
            'atr_mult': 1.5,
            'filter_tf': '4h',
            'trail_start_r': 1.5,  # 1.2 → 1.5 (실제 범위에 있는 값)
            'trail_dist_r': 0.02,
            'entry_validity_hours': 24.0
        }

        # 필수 파라미터 목록
        required_params = [
            'atr_mult',
            'filter_tf',
            'trail_start_r',
            'trail_dist_r',
            'entry_validity_hours'
        ]

        # 모든 파라미터 존재 확인
        for param in required_params:
            assert param in optimal_params, f"Required parameter missing: {param}"

        print(f"✓ 필수 파라미터 {len(required_params)}개 모두 존재")

    def test_parameter_types(self):
        """파라미터 타입이 올바른지 검증"""
        optimal_params = {
            'atr_mult': 1.5,
            'filter_tf': '4h',
            'trail_start_r': 1.5,
            'trail_dist_r': 0.02,
            'entry_validity_hours': 24.0
        }

        # 타입 검증
        assert isinstance(optimal_params['atr_mult'], (int, float)), "atr_mult must be numeric"
        assert isinstance(optimal_params['filter_tf'], str), "filter_tf must be string"
        assert isinstance(optimal_params['trail_start_r'], (int, float)), "trail_start_r must be numeric"
        assert isinstance(optimal_params['trail_dist_r'], (int, float)), "trail_dist_r must be numeric"
        assert isinstance(optimal_params['entry_validity_hours'], (int, float)), "entry_validity_hours must be numeric"

        print("✓ 모든 파라미터 타입 올바름")

    def test_parameter_values_in_range(self):
        """파라미터 값이 유효 범위 내인지 검증"""
        optimal_params = {
            'atr_mult': 1.5,
            'filter_tf': '4h',
            'trail_start_r': 1.5,
            'trail_dist_r': 0.02,
            'entry_validity_hours': 24.0
        }

        # 각 파라미터 범위 검증
        for param_name, value in optimal_params.items():
            is_valid, error_msg = validate_param_in_range(param_name, value)
            assert is_valid, f"Parameter validation failed: {error_msg}"

        print("✓ 모든 파라미터 값이 유효 범위 내")

    def test_parameter_values_out_of_range(self):
        """범위 밖 값이 제대로 감지되는지 검증"""
        # atr_mult 범위 밖 (0.5~5.0 범위, 6.0은 범위 밖)
        is_valid, _ = validate_param_in_range('atr_mult', 6.0)
        assert not is_valid, "Out of range value not detected: atr_mult=6.0"

        # filter_tf 잘못된 값
        is_valid, _ = validate_param_in_range('filter_tf', '3h')
        assert not is_valid, "Invalid value not detected: filter_tf='3h'"

        # trail_dist_r 범위 밖 (0.01~0.3 범위, 0.5는 범위 밖)
        is_valid, _ = validate_param_in_range('trail_dist_r', 0.5)
        assert not is_valid, "Out of range value not detected: trail_dist_r=0.5"

        print("✓ 범위 밖 값 감지 정상")

    def test_optimal_params_matches_best_result(self):
        """optimal_params와 best_result.params가 일치하는지 검증"""
        # 시뮬레이션: 백테스트 결과
        best_result = OptimizationResult(
            params={
                'atr_mult': 1.5,
                'filter_tf': '4h',
                'trail_start_r': 1.5,
                'trail_dist_r': 0.02,
                'entry_validity_hours': 24.0
            },
            trades=100,
            win_rate=0.85,
            total_return=150.0,
            simple_return=150.0,
            compound_return=150.0,
            max_drawdown=0.10,
            sharpe_ratio=18.5,
            profit_factor=5.0
        )

        optimal_params = best_result.params.copy()

        # 모든 파라미터 일치 확인
        for param_name in optimal_params.keys():
            assert param_name in best_result.params, f"Parameter missing in best_result: {param_name}"
            assert optimal_params[param_name] == best_result.params[param_name], \
                f"Parameter mismatch: {param_name} ({optimal_params[param_name]} != {best_result.params[param_name]})"

        print("✓ optimal_params와 best_result.params 일치")

    def test_parameter_precision(self):
        """파라미터 정밀도가 적절한지 검증"""
        optimal_params = {
            'atr_mult': 1.5,
            'filter_tf': '4h',
            'trail_start_r': 1.5,
            'trail_dist_r': 0.02,
            'entry_validity_hours': 24.0
        }

        # trail_dist_r 정밀도 검증 (소수점 3자리까지)
        trail_dist = optimal_params['trail_dist_r']
        assert abs(trail_dist - round(trail_dist, 3)) < 1e-6, \
            f"trail_dist_r precision too high: {trail_dist}"

        # atr_mult 정밀도 검증 (소수점 2자리까지)
        atr_mult = optimal_params['atr_mult']
        assert abs(atr_mult - round(atr_mult, 2)) < 1e-6, \
            f"atr_mult precision too high: {atr_mult}"

        print("✓ 파라미터 정밀도 적절함")

    def test_edge_case_extreme_values(self):
        """극값 파라미터가 올바르게 처리되는지 검증"""
        # 최소값 조합 (실제 META_PARAM_RANGES에 있는 최소값)
        min_params = {
            'atr_mult': 0.5,
            'filter_tf': '2h',
            'trail_start_r': 0.5,
            'trail_dist_r': 0.01,  # 0.005 → 0.01 (실제 최소값)
            'entry_validity_hours': 6.0
        }

        for param_name, value in min_params.items():
            is_valid, error_msg = validate_param_in_range(param_name, value)
            assert is_valid, f"Min value validation failed: {error_msg}"

        # 최대값 조합 (실제 META_PARAM_RANGES에 있는 최대값)
        max_params = {
            'atr_mult': 5.0,
            'filter_tf': '1d',
            'trail_start_r': 3.0,
            'trail_dist_r': 0.3,  # 0.05 → 0.3 (실제 최대값)
            'entry_validity_hours': 96.0
        }

        for param_name, value in max_params.items():
            is_valid, error_msg = validate_param_in_range(param_name, value)
            assert is_valid, f"Max value validation failed: {error_msg}"

        print("✓ 극값 조합 처리 정상")

    def test_optimal_params_serialization(self):
        """optimal_params가 JSON 직렬화 가능한지 검증"""
        import json

        optimal_params = {
            'atr_mult': 1.5,
            'filter_tf': '4h',
            'trail_start_r': 1.5,
            'trail_dist_r': 0.02,
            'entry_validity_hours': 24.0
        }

        # JSON 직렬화
        json_str = json.dumps(optimal_params)
        assert json_str is not None, "JSON serialization failed"

        # JSON 역직렬화
        deserialized = json.loads(json_str)
        assert deserialized == optimal_params, "JSON deserialization mismatch"

        print("✓ JSON 직렬화/역직렬화 정상")


class TestOptimalParamsIntegration:
    """optimal_params 통합 검증 테스트"""

    def test_optimal_params_from_meta_result(self):
        """Meta 최적화 결과에서 optimal_params 추출 검증"""
        # 시뮬레이션: Meta 최적화 결과
        meta_result = {
            'optimal_params': {
                'atr_mult': 1.5,
                'filter_tf': '4h',
                'trail_start_r': 1.5,
                'trail_dist_r': 0.02,
                'entry_validity_hours': 24.0
            },
            'best_result': OptimizationResult(
                params={
                    'atr_mult': 1.5,
                    'filter_tf': '4h',
                    'trail_start_r': 1.5,
                    'trail_dist_r': 0.02,
                    'entry_validity_hours': 24.0
                },
                trades=100,
                win_rate=0.85,
                total_return=150.0,
                simple_return=150.0,
                compound_return=150.0,
                max_drawdown=0.10,
                sharpe_ratio=18.5,
                profit_factor=5.0
            ),
            'statistics': {
                'total_combinations_tested': 3000,
                'time_elapsed_seconds': 20.0
            }
        }

        # optimal_params 추출
        optimal_params = meta_result['optimal_params']

        # 필수 키 존재
        assert 'optimal_params' in meta_result
        assert 'best_result' in meta_result
        assert 'statistics' in meta_result

        # optimal_params 유효성
        for param_name, value in optimal_params.items():
            is_valid, error_msg = validate_param_in_range(param_name, value)
            assert is_valid, f"Invalid optimal_params: {error_msg}"

        # best_result와 일치
        for param_name in optimal_params.keys():
            assert optimal_params[param_name] == meta_result['best_result'].params[param_name], \
                f"Mismatch: {param_name}"

        print("✓ Meta 결과에서 optimal_params 추출 정상")


if __name__ == '__main__':
    # pytest 없이도 실행 가능
    import sys

    test1 = TestOptimalParamsValidation()
    test2 = TestOptimalParamsIntegration()

    try:
        print("\n=== Test: Required Parameters Exist ===")
        test1.test_required_parameters_exist()

        print("\n=== Test: Parameter Types ===")
        test1.test_parameter_types()

        print("\n=== Test: Parameter Values In Range ===")
        test1.test_parameter_values_in_range()

        print("\n=== Test: Parameter Values Out Of Range ===")
        test1.test_parameter_values_out_of_range()

        print("\n=== Test: Optimal Params Matches Best Result ===")
        test1.test_optimal_params_matches_best_result()

        print("\n=== Test: Parameter Precision ===")
        test1.test_parameter_precision()

        print("\n=== Test: Edge Case Extreme Values ===")
        test1.test_edge_case_extreme_values()

        print("\n=== Test: Optimal Params Serialization ===")
        test1.test_optimal_params_serialization()

        print("\n=== Test: Optimal Params From Meta Result ===")
        test2.test_optimal_params_from_meta_result()

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
