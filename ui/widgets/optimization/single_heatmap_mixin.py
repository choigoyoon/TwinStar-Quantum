"""
SingleOptimizationWidget 히트맵 Mixin

2D 그리드 히트맵 표시 관련 메서드를 분리한 Mixin 클래스

v7.26.8 (2026-01-19): Phase 4-4 - 히트맵 Mixin 분리
"""

from typing import List, Dict, Any

from utils.logger import get_module_logger
logger = get_module_logger(__name__)


class SingleOptimizationHeatmapMixin:
    """
    SingleOptimizationWidget 히트맵 Mixin

    2D 그리드 검증 및 히트맵 표시 메서드를 제공합니다.
    """

    # Type hint for attribute that will be provided by SingleOptimizationWidget
    heatmap_viewer: Any  # HeatmapViewer

    def _is_2d_grid(self, results: list) -> bool:
        """
        2D 그리드 여부 확인 (변경된 파라미터가 정확히 2개인지)

        Args:
            results: 최적화 결과 리스트

        Returns:
            True: 2D 그리드 (히트맵 표시 가능)
            False: 1D/3D+ 그리드
        """
        if not results or len(results) < 4:
            return False

        # 첫 번째 결과를 기준으로 파라미터 추출
        if isinstance(results[0], dict):
            base_params = results[0].get('params', {})
        else:
            base_params = getattr(results[0], 'params', {})

        if not base_params:
            return False

        # 각 파라미터별로 고유 값 개수 세기
        param_unique_values = {key: set() for key in base_params.keys()}

        for result in results:
            if isinstance(result, dict):
                params = result.get('params', {})
            else:
                params = getattr(result, 'params', {})

            for key, value in params.items():
                if key in param_unique_values:
                    param_unique_values[key].add(value)

        # 고유 값이 2개 이상인 파라미터 개수 확인
        varying_params = [
            key for key, values in param_unique_values.items()
            if len(values) >= 2
        ]

        # 정확히 2개 파라미터만 변경되었을 때 2D 그리드
        return len(varying_params) == 2

    def _show_heatmap(self, results: list):
        """
        2D 히트맵 표시

        Args:
            results: 최적화 결과 리스트
        """
        try:
            from ui.widgets.optimization.heatmap import HeatmapViewer
            import numpy as np

            # 첫 번째 결과에서 기준 파라미터 추출
            if isinstance(results[0], dict):
                base_params = results[0].get('params', {})
            else:
                base_params = getattr(results[0], 'params', {})

            # 변경된 파라미터 2개 찾기
            param_unique_values = {key: set() for key in base_params.keys()}

            for result in results:
                if isinstance(result, dict):
                    params = result.get('params', {})
                else:
                    params = getattr(result, 'params', {})

                for key, value in params.items():
                    if key in param_unique_values:
                        param_unique_values[key].add(value)

            varying_params = [
                key for key, values in param_unique_values.items()
                if len(values) >= 2
            ]

            if len(varying_params) != 2:
                logger.warning("2D 그리드가 아닙니다 (변경된 파라미터 개수 != 2)")
                return

            param1_name, param2_name = varying_params[0], varying_params[1]

            # 파라미터 값 정렬
            param1_values = sorted(list(param_unique_values[param1_name]))
            param2_values = sorted(list(param_unique_values[param2_name]))

            # 히트맵 행렬 생성 (Sharpe Ratio 기준)
            heatmap_data = np.full((len(param2_values), len(param1_values)), np.nan)

            for result in results:
                if isinstance(result, dict):
                    params = result.get('params', {})
                    sharpe = result.get('sharpe_ratio', 0.0)
                else:
                    params = getattr(result, 'params', {})
                    sharpe = getattr(result, 'sharpe_ratio', 0.0)

                p1_val = params.get(param1_name)
                p2_val = params.get(param2_name)

                if p1_val in param1_values and p2_val in param2_values:
                    x_idx = param1_values.index(p1_val)
                    y_idx = param2_values.index(p2_val)
                    heatmap_data[y_idx, x_idx] = sharpe

            # 라벨 생성
            x_labels = [f"{param1_name}={v}" for v in param1_values]
            y_labels = [f"{param2_name}={v}" for v in param2_values]

            # 히트맵 뷰어 생성 및 표시
            self.heatmap_viewer = HeatmapViewer()
            self.heatmap_viewer.setWindowTitle(
                f"최적화 히트맵 ({param1_name} × {param2_name})"
            )
            self.heatmap_viewer.resize(900, 700)
            self.heatmap_viewer.update_heatmap(heatmap_data, x_labels, y_labels)
            self.heatmap_viewer.show()

            logger.info(f"✅ 히트맵 표시 완료: {param1_name} × {param2_name}")

        except Exception as e:
            logger.error(f"❌ 히트맵 표시 실패: {e}", exc_info=True)


__all__ = ['SingleOptimizationHeatmapMixin']
