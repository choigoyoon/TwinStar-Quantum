"""
tests/test_optimizer_defensive.py

런타임 에러 방어 코드 단위 테스트
(v7.19 - UI 최적화 런타임 에러 수정)
"""

import unittest
from typing import Dict, List


class TestOptimizerDefensive(unittest.TestCase):
    """optimizer.py 방어 코드 테스트"""

    def test_generate_full_grid_none_handling(self):
        """generate_full_grid() None 반환 시 기본값 제공 확인"""
        from core.optimizer import generate_full_grid

        grid = generate_full_grid('1h', 20.0)

        # 모든 키가 None이 아닌지 확인
        assert grid['filter_tf'] is not None, "filter_tf must not be None"
        assert grid['atr_mult'] is not None, "atr_mult must not be None"
        assert grid['trail_start_r'] is not None, "trail_start_r must not be None"
        assert grid['trail_dist_r'] is not None, "trail_dist_r must not be None"
        assert grid['entry_validity_hours'] is not None, "entry_validity_hours must not be None"

        # 모든 값이 리스트인지 확인
        for key, value in grid.items():
            assert isinstance(value, list), f"{key} must be list, got {type(value)}"
            assert len(value) > 0, f"{key} must not be empty"

    def test_generate_quick_grid_none_handling(self):
        """generate_quick_grid() None 반환 시 기본값 제공 확인"""
        from core.optimizer import generate_quick_grid

        grid = generate_quick_grid('1h', 20.0)

        # 모든 키가 None이 아닌지 확인
        assert grid['filter_tf'] is not None
        assert grid['atr_mult'] is not None
        assert grid['trail_start_r'] is not None
        assert grid['trail_dist_r'] is not None
        assert grid['entry_validity_hours'] is not None

        # 모든 값이 리스트인지 확인
        for key, value in grid.items():
            assert isinstance(value, list), f"{key} must be list, got {type(value)}"
            assert len(value) > 0, f"{key} must not be empty"

    def test_generate_deep_grid_none_handling(self):
        """generate_deep_grid() None 반환 시 기본값 제공 확인"""
        from core.optimizer import generate_deep_grid

        grid = generate_deep_grid('1h', 20.0)

        # 모든 키가 None이 아닌지 확인
        assert grid['filter_tf'] is not None
        assert grid['atr_mult'] is not None
        assert grid['trail_start_r'] is not None
        assert grid['trail_dist_r'] is not None
        assert grid['entry_validity_hours'] is not None

        # 모든 값이 리스트인지 확인
        for key, value in grid.items():
            assert isinstance(value, list), f"{key} must be list, got {type(value)}"
            assert len(value) > 0, f"{key} must not be empty"


class TestOptimizationLogicDefensive(unittest.TestCase):
    """optimization_logic.py 방어 코드 테스트"""

    def test_generate_grid_from_options_none_filtering(self):
        """generate_grid_from_options() None 값 필터링 확인"""
        from core.optimization_logic import OptimizationEngine

        engine = OptimizationEngine(strategy=None)

        # None 포함 옵션
        param_options = {
            'filter_tf': None,  # None
            'atr_mult': [1.5, 2.0],
            'trail_start_r': [],  # 빈 리스트
            'leverage': [1]
        }

        grid = engine.generate_grid_from_options(param_options)

        # 빈 그리드가 아니어야 함
        assert len(grid) > 0, "Grid must not be empty"

        # 모든 파라미터에 기본값 존재
        for params in grid:
            assert 'filter_tf' in params, "filter_tf must exist (filled with default)"
            assert 'atr_mult' in params
            assert 'leverage' in params

    def test_generate_grid_from_options_empty_options(self):
        """generate_grid_from_options() 모든 값이 None일 때 빈 그리드 반환"""
        from core.optimization_logic import OptimizationEngine

        engine = OptimizationEngine(strategy=None)

        # 모든 값이 None
        param_options = {
            'unknown_param1': None,
            'unknown_param2': [],
        }

        grid = engine.generate_grid_from_options(param_options)

        # 빈 그리드 반환 (에러 없이)
        assert grid == [], "Grid must be empty when all params are None/empty"

    def test_generate_grid_from_options_valid_lists(self):
        """generate_grid_from_options() 유효한 리스트 처리 확인"""
        from core.optimization_logic import OptimizationEngine

        engine = OptimizationEngine(strategy=None)

        param_options = {
            'filter_tf': ['4h', '12h'],
            'atr_mult': [1.5, 2.0],
            'leverage': [1]
        }

        grid = engine.generate_grid_from_options(param_options)

        # 조합 수: 2 × 2 × 1 = 4
        assert len(grid) == 4, f"Expected 4 combinations, got {len(grid)}"

        # 모든 파라미터 존재 확인
        for params in grid:
            assert 'filter_tf' in params
            assert 'atr_mult' in params
            assert 'leverage' in params


class TestTimeoutHandling(unittest.TestCase):
    """타임아웃 처리 테스트"""

    def test_timeout_sufficient_for_slow_tasks(self):
        """future.result(timeout=10) 충분성 확인"""
        import time
        from concurrent.futures import ProcessPoolExecutor, as_completed

        def slow_task(x):
            """0.5초 걸리는 느린 작업 (대형 DataFrame 백테스트 시뮬레이션)"""
            time.sleep(0.5)
            return x * 2

        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(slow_task, i) for i in range(10)]

            results = []
            for future in as_completed(futures):
                # timeout=10 사용 (실제 코드와 동일)
                result = future.result(timeout=10)
                results.append(result)

        # 모든 결과 수집됨 (타임아웃 없음)
        assert len(results) == 10, f"Expected 10 results, got {len(results)}"
        assert results == [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]


class TestPythonVersionCompatibility(unittest.TestCase):
    """Python 버전 호환성 테스트"""

    def test_executor_shutdown_compatibility(self):
        """ProcessPoolExecutor.shutdown() 버전 호환성 확인"""
        import sys
        from concurrent.futures import ProcessPoolExecutor

        with ProcessPoolExecutor(max_workers=2) as executor:
            # Python 버전 체크
            if sys.version_info >= (3, 9):
                # Python 3.9+: cancel_futures 파라미터 지원
                try:
                    executor.shutdown(wait=False, cancel_futures=True)
                    assert True, "Python 3.9+ shutdown with cancel_futures succeeded"
                except TypeError:
                    self.fail("Python 3.9+ should support cancel_futures parameter")
            else:
                # Python 3.8 이하: cancel_futures 미지원
                try:
                    executor.shutdown(wait=False)
                    assert True, "Python 3.8 shutdown without cancel_futures succeeded"
                except Exception as e:
                    self.fail(f"Python 3.8 shutdown failed: {e}")


# ==================== 통합 테스트 ====================

class TestIntegration(unittest.TestCase):
    """통합 테스트 (UI → optimizer → optimization_logic 전체 흐름)"""

    def test_full_optimization_flow_quick_mode(self):
        """Quick 모드 전체 최적화 흐름 테스트"""
        from core.optimizer import generate_grid_by_mode
        from core.optimization_logic import OptimizationEngine

        # 1. Grid 생성
        grid_options = generate_grid_by_mode(trend_tf='1h', mode='quick')

        # None 체크
        assert grid_options is not None
        assert all(v is not None for v in grid_options.values())

        # 2. Engine 생성
        engine = OptimizationEngine(strategy=None)

        # 3. Grid 확장
        grid = engine.generate_grid_from_options(grid_options)

        # 조합 수 확인 (Quick: 8개)
        assert len(grid) > 0, "Quick mode grid must not be empty"
        assert len(grid) <= 10, f"Quick mode grid too large: {len(grid)}"

    def test_full_optimization_flow_standard_mode(self):
        """Standard 모드 전체 최적화 흐름 테스트"""
        from core.optimizer import generate_grid_by_mode
        from core.optimization_logic import OptimizationEngine

        # 1. Grid 생성
        grid_options = generate_grid_by_mode(trend_tf='1h', mode='standard')

        # None 체크
        assert grid_options is not None
        assert all(v is not None for v in grid_options.values())

        # 2. Engine 생성
        engine = OptimizationEngine(strategy=None)

        # 3. Grid 확장
        grid = engine.generate_grid_from_options(grid_options)

        # 조합 수 확인 (Standard: 60개)
        assert len(grid) > 0, "Standard mode grid must not be empty"
        assert 50 <= len(grid) <= 150, f"Standard mode grid size unexpected: {len(grid)}"

    def test_full_optimization_flow_deep_mode(self):
        """Deep 모드 전체 최적화 흐름 테스트"""
        from core.optimizer import generate_grid_by_mode
        from core.optimization_logic import OptimizationEngine

        # 1. Grid 생성
        grid_options = generate_grid_by_mode(trend_tf='1h', mode='deep')

        # None 체크
        assert grid_options is not None
        assert all(v is not None for v in grid_options.values())

        # 2. Engine 생성
        engine = OptimizationEngine(strategy=None)

        # 3. Grid 확장
        grid = engine.generate_grid_from_options(grid_options)

        # 조합 수 확인 (Deep: 1,080개)
        assert len(grid) > 0, "Deep mode grid must not be empty"
        assert 1000 <= len(grid) <= 1200, f"Deep mode grid size unexpected: {len(grid)}"


if __name__ == '__main__':
    unittest.main()
