"""
SingleOptimizationWidget 헬퍼 Mixin

결과 처리 헬퍼 메서드를 분리한 Mixin 클래스

v7.26.8 (2026-01-19): Phase 4-4 - 헬퍼 Mixin 분리
"""

from typing import Dict

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


class SingleOptimizationHelpersMixin:
    """
    SingleOptimizationWidget 헬퍼 Mixin

    결과 그룹화 등 헬퍼 메서드를 제공합니다.
    """

    def _group_similar_results(self, results: list) -> Dict[int, int]:
        """비슷한 결과를 그룹화 (파라미터 유사도 기준)

        Returns:
            Dict[result_index, group_id]: 각 결과의 그룹 ID
        """
        groups: Dict[int, int] = {}
        group_id = 0

        for i, result1 in enumerate(results):
            if i in groups:
                continue

            # 새 그룹 시작
            groups[i] = group_id

            # 유사한 결과 찾기
            params1 = result1.get('params', {}) if isinstance(result1, dict) else getattr(result1, 'params', {})

            for j in range(i + 1, len(results)):
                if j in groups:
                    continue

                params2 = results[j].get('params', {}) if isinstance(results[j], dict) else getattr(results[j], 'params', {})

                # 파라미터 유사도 체크 (핵심 3개 파라미터)
                similar = True
                for key in ['filter_tf', 'atr_mult', 'trail_start_r']:
                    val1 = params1.get(key)
                    val2 = params2.get(key)

                    if key == 'filter_tf':
                        # 타임프레임은 정확히 일치
                        if val1 != val2:
                            similar = False
                            break
                    else:
                        # 숫자는 ±10% 이내
                        if val1 and val2:
                            if abs(val1 - val2) / max(abs(val1), 0.01) > 0.1:
                                similar = False
                                break

                if similar:
                    groups[j] = group_id

            group_id += 1

        return groups


__all__ = ['SingleOptimizationHelpersMixin']
