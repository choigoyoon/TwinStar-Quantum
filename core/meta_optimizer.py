"""메타 최적화 엔진 - 파라미터 범위 자동 탐색

이 모듈은 메타 최적화 (Meta-Optimization) 시스템을 구현합니다.
랜덤 샘플링 + 백분위수 기반 범위 추출로 최적 파라미터 범위를 자동 탐색합니다.

Architecture:
    Level 1: 넓은 범위 랜덤 샘플링 (1,000개 조합)
    Level 2: 상위 10% 결과 분석 (백분위수 10~90%)
    Level 3: 범위 축소 + 반복 (수렴 조건 충족시 종료)

Author: Claude Sonnet 4.5
Version: 1.0.0
Date: 2026-01-17
"""

import time
import random
import itertools
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Callable, Union
from collections import Counter
from datetime import datetime
import json
import os

from utils.logger import get_module_logger

logger = get_module_logger(__name__)


class MetaOptimizer:
    """메타 최적화 엔진 - 파라미터 범위 자동 탐색

    랜덤 샘플링과 백분위수 기반 범위 추출을 사용하여 최적 파라미터 범위를 자동으로 탐색합니다.

    Attributes:
        base_optimizer: 기존 BacktestOptimizer 인스턴스
        meta_ranges: 메타 범위 (META_PARAM_RANGES)
        sample_size: 반복당 샘플 수 (기본 1,000개)
        min_improvement: 수렴 기준 (기본 5%)
        max_iterations: 최대 반복 횟수 (기본 3회)
        iteration_results: 반복별 최고 점수 리스트
        extracted_ranges: 추출된 범위

    Example:
        >>> from core.optimizer import BacktestOptimizer
        >>> from core.meta_optimizer import MetaOptimizer
        >>> from core.strategy_core import AlphaX7Core
        >>>
        >>> # 기존 Optimizer 생성
        >>> base_optimizer = BacktestOptimizer(AlphaX7Core, df)
        >>>
        >>> # Meta Optimizer 생성
        >>> meta = MetaOptimizer(
        ...     base_optimizer=base_optimizer,
        ...     sample_size=1000,
        ...     max_iterations=3
        ... )
        >>>
        >>> # 메타 최적화 실행
        >>> result = meta.run_meta_optimization(df, metric='sharpe_ratio')
        >>>
        >>> # 추출된 범위 확인
        >>> print(result['extracted_ranges'])
        >>> # {'atr_mult': {'quick': [1.2, 2.4], 'standard': [1.2, 1.8, 2.4], ...}}
    """

    def __init__(
        self,
        base_optimizer,  # BacktestOptimizer 인스턴스
        meta_ranges: Optional[Dict[str, List]] = None,
        sample_size: int = 1000,
        min_improvement: float = 0.05,
        max_iterations: int = 3
    ):
        """MetaOptimizer 초기화

        Args:
            base_optimizer: 기존 BacktestOptimizer 인스턴스 (재사용)
            meta_ranges: META_PARAM_RANGES (기본값: config.meta_ranges 사용)
            sample_size: 반복당 랜덤 샘플 수 (기본 1,000개)
            min_improvement: 수렴 기준 (기본 5%)
            max_iterations: 최대 반복 횟수 (기본 3회)
        """
        self.base_optimizer = base_optimizer

        # META_PARAM_RANGES 로드
        if meta_ranges is None:
            from config.meta_ranges import load_meta_param_ranges
            meta_ranges = load_meta_param_ranges()
        self.meta_ranges = meta_ranges

        self.sample_size = sample_size
        self.min_improvement = min_improvement
        self.max_iterations = max_iterations

        # 상태 변수
        self.iteration_results: List[float] = []  # 반복별 최고 점수
        self.extracted_ranges: Optional[Dict[str, List]] = None  # 추출된 범위

    def run_meta_optimization(
        self,
        df: pd.DataFrame,
        trend_tf: str = '1h',
        metric: str = 'sharpe_ratio',
        callback: Optional[Callable] = None
    ) -> Dict:
        """메타 최적화 메인 루프

        Args:
            df: OHLCV 데이터프레임
            trend_tf: 추세 타임프레임 (기본 '1h')
            metric: 최적화 목표 지표 ('sharpe_ratio', 'win_rate', 'profit_factor' 등)
            callback: 진행 상황 콜백 함수 (event: str, *args)

        Returns:
            {
                'extracted_ranges': {...},  # PARAM_RANGES_BY_MODE 형식
                'best_result': OptimizationResult,
                'iterations': int,
                'convergence_reason': str,
                'statistics': {
                    'total_combinations_tested': int,
                    'time_elapsed_seconds': float,
                    'convergence_iterations': int,
                    'top_score_history': List[float]
                }
            }

        Raises:
            ValueError: 데이터가 비어있거나 유효하지 않을 때
        """
        if df is None or df.empty:
            raise ValueError("데이터가 비어있습니다")

        logger.info(
            f"🔍 Meta-Optimization Started: {self.sample_size} samples × {self.max_iterations} iterations"
        )
        start_time = time.time()
        iteration = 0
        convergence_reason = 'max_iterations_reached'

        while iteration < self.max_iterations:
            iteration += 1

            if callback:
                callback('iteration_started', iteration, self.sample_size)

            logger.info(f"  Iteration {iteration}/{self.max_iterations} started")

            # 1. 랜덤 샘플링 그리드 생성
            if iteration == 1:
                # 첫 반복: META_PARAM_RANGES 사용
                grid = self._generate_random_sample(self.meta_ranges)
            else:
                # 이후 반복: 추출된 범위 사용
                if self.extracted_ranges is None:
                    logger.warning("  추출된 범위가 없습니다. 첫 반복 범위 재사용.")
                    grid = self._generate_random_sample(self.meta_ranges)
                else:
                    grid = self._generate_random_sample(self.extracted_ranges)

            # 2. 백테스트 실행 (기존 Optimizer 재사용)
            logger.info(f"  Running backtest: {len(grid[list(grid.keys())[0]])} unique combos")

            results = self.base_optimizer.run_optimization(
                df=df,
                grid=grid,
                metric=metric,
                mode='custom'
            )

            if not results:
                logger.warning(f"  Iteration {iteration}: No valid results")
                break

            # 3. 최고 점수 기록
            best_score = getattr(results[0], metric)
            self.iteration_results.append(best_score)

            if callback:
                callback('iteration_finished', iteration, len(results), best_score)

            logger.info(
                f"  Iteration {iteration} finished: {len(results)} results, "
                f"best {metric}={best_score:.2f}"
            )

            # 4. 범위 추출 (상위 10%)
            top_count = max(1, len(results) // 10)
            top_results = results[:top_count]
            self.extracted_ranges = self._extract_ranges_from_top_results(top_results)

            logger.info(f"  Extracted ranges from top {top_count} results")

            # 5. 수렴 체크
            if self._check_convergence():
                convergence_reason = 'improvement_below_threshold'
                logger.info(f"  ✅ Converged at iteration {iteration} (improvement < {self.min_improvement * 100}%)")
                break

        # 6. PARAM_RANGES_BY_MODE 변환
        if self.extracted_ranges is None:
            logger.error("  메타 최적화 실패: 추출된 범위가 없습니다")
            raise RuntimeError("Meta-optimization failed: No extracted ranges")

        final_ranges = self._convert_to_param_ranges_by_mode(self.extracted_ranges)

        elapsed = time.time() - start_time

        logger.info(
            f"🎉 Meta-Optimization Completed: {iteration} iterations, "
            f"{elapsed:.1f}s, reason={convergence_reason}"
        )

        return {
            'extracted_ranges': final_ranges,
            'best_result': results[0] if results else None,
            'iterations': iteration,
            'convergence_reason': convergence_reason,
            'statistics': {
                'total_combinations_tested': iteration * self.sample_size,
                'time_elapsed_seconds': elapsed,
                'convergence_iterations': iteration,
                'top_score_history': self.iteration_results
            }
        }

    def _generate_random_sample(
        self,
        ranges: Dict[str, List]
    ) -> Dict[str, List]:
        """랜덤 샘플링으로 그리드 생성

        전체 조합에서 sample_size 개만큼 랜덤 샘플링하여 그리드를 생성합니다.

        Args:
            ranges: 파라미터 범위 (META_PARAM_RANGES 또는 extracted_ranges)

        Returns:
            샘플링된 그리드 (Dict[파라미터명, List[값]])

        Example:
            >>> ranges = {'atr_mult': [1.0, 1.5, 2.0], 'filter_tf': ['4h', '6h']}
            >>> grid = self._generate_random_sample(ranges)
            >>> # 전체 6개 조합 중 min(sample_size, 6)개 샘플링
        """
        # 전체 조합 생성
        all_combinations = list(itertools.product(*ranges.values()))

        # 샘플 수 결정 (전체 조합 수와 sample_size 중 작은 값)
        actual_sample_size = min(self.sample_size, len(all_combinations))

        # 랜덤 샘플링
        sampled_combos = random.sample(all_combinations, actual_sample_size)

        # Dict 형식으로 변환 (각 파라미터별 고유 값만 추출)
        param_names = list(ranges.keys())
        grid = {name: [] for name in param_names}

        for combo in sampled_combos:
            for i, name in enumerate(param_names):
                if combo[i] not in grid[name]:
                    grid[name].append(combo[i])

        logger.info(f"    Sampled {actual_sample_size} combinations from {len(all_combinations)} total")

        return grid

    def _extract_ranges_from_top_results(
        self,
        top_results  # List[OptimizationResult]
    ) -> Dict[str, List]:
        """백분위수 기반 범위 추출

        상위 결과의 파라미터 분포를 분석하여 새로운 범위를 추출합니다.

        Args:
            top_results: 상위 10% 최적화 결과 리스트

        Returns:
            추출된 범위 (Dict[파라미터명, List[값]])

        Algorithm:
            - 수치형: 10~90% 백분위수 기반 5개 균등 샘플링
            - 카테고리형: 빈도 상위 5개 선택

        Example:
            >>> top_results = [...]  # 100개 결과
            >>> ranges = self._extract_ranges_from_top_results(top_results)
            >>> # {'atr_mult': [1.2, 1.5, 1.8, 2.1, 2.4], 'filter_tf': ['4h', '6h', '12h']}
        """
        new_ranges = {}

        for param in self.meta_ranges.keys():
            # 상위 결과에서 파라미터 값 추출
            values = [r.params[param] for r in top_results]

            if isinstance(values[0], str):
                # 카테고리형 (filter_tf)
                counts = Counter(values)
                new_ranges[param] = [v for v, c in counts.most_common(5)]
                logger.info(f"    {param} (categorical): {new_ranges[param]}")
            else:
                # 수치형 (atr_mult, trail_start_r, trail_dist_r, entry_validity_hours)
                p10 = np.percentile(values, 10)  # 하위 10% 제거
                p90 = np.percentile(values, 90)  # 상위 10% 제거
                new_ranges[param] = np.linspace(p10, p90, 5).tolist()  # 5개 균등 샘플링
                logger.info(f"    {param} (numeric): [{p10:.2f}, ..., {p90:.2f}]")

        return new_ranges

    def _convert_to_param_ranges_by_mode(
        self,
        ranges: Dict[str, List]
    ) -> Dict:
        """PARAM_RANGES_BY_MODE 형식으로 변환

        추출된 범위를 Quick/Standard/Deep 모드별 범위로 변환합니다.

        Args:
            ranges: 추출된 범위 (5개 값)

        Returns:
            PARAM_RANGES_BY_MODE 형식
            {
                'atr_mult': {
                    'quick': [1.2, 2.4],               # 양 끝
                    'standard': [1.2, 1.8, 2.4],       # 시작/중간/끝
                    'deep': [1.2, 1.5, 1.8, 2.1, 2.4]  # 전체
                }
            }

        Algorithm:
            - Quick: 2개 (양 끝)
            - Standard: 3개 (시작, 중간, 끝)
            - Deep: 5개 (전체)
        """
        result = {}

        for param, values in ranges.items():
            if isinstance(values[0], str):
                # 카테고리형
                n = len(values)
                result[param] = {
                    'quick': values[:2] if n >= 2 else values,
                    'standard': values[:3] if n >= 3 else values,
                    'deep': values
                }
            else:
                # 수치형
                n = len(values)
                result[param] = {
                    'quick': [values[0], values[-1]],  # 양 끝
                    'standard': [values[0], values[n//2], values[-1]],  # 시작/중간/끝
                    'deep': values  # 전체
                }

        return result

    def _check_convergence(self) -> bool:
        """수렴 조건 체크

        최근 2회 반복의 개선율이 모두 min_improvement (기본 5%) 미만이면 수렴으로 판단합니다.

        Returns:
            True: 수렴 완료
            False: 추가 반복 필요

        Algorithm:
            1. 최소 2회 반복 완료 필요
            2. 최근 2회 개선율 계산
            3. 모두 < min_improvement이면 수렴

        Example:
            >>> self.iteration_results = [18.0, 18.72, 19.09]
            >>> # 개선율: +4.0%, +2.0% → 수렴!
        """
        if len(self.iteration_results) < 2:
            return False

        improvements = []
        for i in range(-2, 0):  # 최근 2회
            prev = self.iteration_results[i - 1]
            curr = self.iteration_results[i]

            if prev == 0:
                improvement = 0
            else:
                improvement = (curr - prev) / prev

            improvements.append(improvement)

        # 모두 min_improvement 미만이면 수렴
        return all(imp < self.min_improvement for imp in improvements)

    def save_meta_ranges(
        self,
        exchange: str,
        symbol: str,
        timeframe: str,
        output_dir: str = 'presets/meta_ranges'
    ) -> str:
        """메타 범위를 JSON으로 저장

        Args:
            exchange: 거래소명 (예: 'bybit')
            symbol: 심볼명 (예: 'BTCUSDT')
            timeframe: 타임프레임 (예: '1h')
            output_dir: 저장 디렉토리 (기본: 'presets/meta_ranges')

        Returns:
            저장된 파일 경로

        Example:
            >>> meta.save_meta_ranges('bybit', 'BTCUSDT', '1h')
            'presets/meta_ranges/bybit_BTCUSDT_1h_meta_20260117_180000.json'
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{exchange}_{symbol}_{timeframe}_meta_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)

        data = {
            'meta_optimization_id': f"{exchange}_{symbol}_{timeframe}_meta_{timestamp}",
            'created_at': datetime.now().isoformat(),
            'meta_method': 'random_sampling_percentile',
            'exchange': exchange,
            'symbol': symbol,
            'timeframe': timeframe,
            'iterations': len(self.iteration_results),
            'convergence_reason': 'improvement_below_threshold' if self._check_convergence() else 'max_iterations_reached',
            'extracted_ranges': self.extracted_ranges,
            'param_ranges_by_mode': self._convert_to_param_ranges_by_mode(self.extracted_ranges) if self.extracted_ranges else {},
            'statistics': {
                'total_combinations_tested': len(self.iteration_results) * self.sample_size,
                'time_elapsed_seconds': 0,  # 호출 시점에서는 계산 불가
                'convergence_iterations': len(self.iteration_results),
                'top_score_history': self.iteration_results,
                'sample_size': self.sample_size,
                'min_improvement': self.min_improvement,
                'max_iterations': self.max_iterations
            }
        }

        # 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)

        # JSON 저장
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info(f"✅ Meta ranges saved: {filepath}")

        return filepath


if __name__ == '__main__':
    # 테스트 실행
    print("=== MetaOptimizer Test ===")
    print("This module requires BacktestOptimizer instance.")
    print("Usage:")
    print("  from core.meta_optimizer import MetaOptimizer")
    print("  meta = MetaOptimizer(base_optimizer)")
    print("  result = meta.run_meta_optimization(df)")
