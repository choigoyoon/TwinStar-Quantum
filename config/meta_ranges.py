"""메타 최적화 기본 범위 정의 (SSOT)

이 모듈은 메타 최적화에서 사용할 파라미터 범위를 정의합니다.
문헌 기반 범위를 사용하여 전역 최적값 탐색을 지원합니다.

Author: Claude Sonnet 4.5
Version: 1.0.0
Date: 2026-01-17
"""

from typing import Dict, List, Union

# 메타 최적화 기본 범위 (문헌 기반)
META_PARAM_RANGES: Dict[str, List[Union[float, str]]] = {
    # ATR 배수 (손절 거리)
    # 문헌 기반: 0.5~5.0 (Wilder 1978, 금융공학 표준)
    'atr_mult': [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0],

    # 필터 타임프레임 (MTF 추세 필터)
    # 2시간 ~ 1일 (일반적인 트레이딩 타임프레임)
    'filter_tf': ['2h', '4h', '6h', '12h', '1d'],

    # 트레일링 시작 배수 (익절 시작 지점)
    # 0.5R ~ 3.0R (리스크 대비 수익)
    'trail_start_r': [0.5, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0],

    # 트레일링 간격 (익절 추적 간격)
    # 5% ~ 30% (ATR 대비 비율)
    'trail_dist_r': [0.05, 0.1, 0.15, 0.2, 0.25, 0.3],

    # 진입 유효시간 (패턴 유효 기간)
    # 6시간 ~ 96시간 (4일)
    'entry_validity_hours': [6, 12, 24, 36, 48, 72, 96]
}


def load_meta_param_ranges() -> Dict[str, List[Union[float, str]]]:
    """메타 범위 로드 (동적 조정 가능)

    Returns:
        메타 파라미터 범위 딕셔너리 (복사본)

    Note:
        복사본을 반환하여 원본 보호
    """
    return META_PARAM_RANGES.copy()


def get_meta_range_info() -> Dict[str, Dict[str, Union[int, float]]]:
    """메타 범위 통계 정보 반환

    Returns:
        각 파라미터의 통계 정보
        - count: 값 개수
        - min: 최소값 (수치형만)
        - max: 최대값 (수치형만)
    """
    info = {}

    for param, values in META_PARAM_RANGES.items():
        if isinstance(values[0], (int, float)):
            info[param] = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'type': 'numeric'
            }
        else:
            info[param] = {
                'count': len(values),
                'type': 'categorical',
                'values': values
            }

    return info


def get_total_combinations() -> int:
    """전체 조합 수 계산

    Returns:
        메타 범위의 전체 조합 수

    Example:
        10 × 5 × 7 × 6 × 7 = 14,700개
    """
    total = 1
    for values in META_PARAM_RANGES.values():
        total *= len(values)
    return total


if __name__ == '__main__':
    # 테스트 실행
    print("=== Meta Parameter Ranges ===")
    for param, values in META_PARAM_RANGES.items():
        print(f"{param}: {len(values)} values")
        print(f"  Range: {values}")

    print(f"\nTotal combinations: {get_total_combinations():,}")

    print("\n=== Range Info ===")
    import json
    print(json.dumps(get_meta_range_info(), indent=2))
