"""
core/coarse_to_fine_optimizer.py
2단계 Coarse-to-Fine 최적화 엔진 (v7.28)

Author: Claude Sonnet 4.5
Date: 2026-01-20
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Tuple
from itertools import product
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass

from config.parameters import DEFAULT_PARAMS, PARAMETER_SENSITIVITY_WEIGHTS
from config.constants.trading import TOTAL_COST
from core.optimizer import OptimizationResult, _worker_run_single
from utils.logger import get_module_logger

logger = get_module_logger(__name__)


# ============ 범위 검증 규칙 ============
ALLOWED_FILTER_TF = ['4h', '6h', '8h', '12h', '1d']
MIN_ENTRY_VALIDITY = 24  # 최소 대기 시간 (시간)
MAX_ENTRY_VALIDITY = 96  # 최대 대기 시간 (시간)


@dataclass
class CoarseFineResult:
    """Coarse-to-Fine 최적화 결과"""
    stage1_results: List[OptimizationResult]
    stage2_results: List[OptimizationResult]
    best_params: dict
    best_metrics: dict
    total_combinations: int
    elapsed_seconds: float
    csv_path: str | None = None


class CoarseToFineOptimizer:
    """2단계 Coarse-to-Fine 최적화 엔진

    Stage 1: Coarse Grid (넓은 범위, 적은 조합)
    Stage 2: Fine-Tuning (좁은 범위, 많은 조합)

    Example:
        >>> from core.data_manager import BotDataManager
        >>> dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
        >>> dm.load_historical()
        >>>
        >>> optimizer = CoarseToFineOptimizer(dm.df_entry_full)
        >>> result = optimizer.run(n_cores=8)
        >>>
        >>> print(f"최적 파라미터: {result.best_params}")
        >>> print(f"Sharpe: {result.best_metrics['sharpe']:.2f}")
    """

    def __init__(
        self,
        df: pd.DataFrame,
        strategy_class=None,
        strategy_type: str = 'macd'
    ):
        """초기화

        Args:
            df: OHLCV DataFrame (1시간봉)
            strategy_class: 전략 클래스 (기본값: AlphaX7Core)
            strategy_type: 전략 타입 ('macd', 'adx', 등)
        """
        self.df = df
        self.strategy_type = strategy_type

        if strategy_class is None:
            from core.strategy_core import AlphaX7Core
            strategy_class = AlphaX7Core

        self.strategy_class = strategy_class

        # Baseline 파라미터
        self.baseline_params = DEFAULT_PARAMS.copy()
        self.baseline_params['leverage'] = 1
        self.baseline_params['macd_fast'] = 6
        self.baseline_params['macd_slow'] = 18
        self.baseline_params['macd_signal'] = 7

    def build_coarse_ranges(self) -> Dict[str, List]:
        """Stage 1: Coarse Grid 범위 생성

        근거:
        - filter_tf: ['4h', '6h', '8h', '12h'] - 설계 범위
        - entry_validity_hours: [48, 72] - 중장기 대기
        - atr_mult: [0.9, 1.0, 1.1, 1.25] - 손절 배수 핵심 범위
        - trail_start_r: [0.4, 0.6, 0.8, 1.0] - 트레일링 시작 배수
        - trail_dist_r: [0.03, 0.05, 0.08, 0.1] - 트레일링 간격

        Returns:
            파라미터 범위 딕셔너리 (512개 조합)
        """
        return {
            'atr_mult': [0.9, 1.0, 1.1, 1.25],
            'filter_tf': ['4h', '6h', '8h', '12h'],
            'entry_validity_hours': [48, 72],
            'trail_start_r': [0.4, 0.6, 0.8, 1.0],
            'trail_dist_r': [0.03, 0.05, 0.08, 0.1]
        }

    def build_fine_ranges(self, coarse_optimal: Dict) -> Dict[str, List]:
        """Stage 2: Fine-Tuning 범위 생성

        근거:
        - filter_tf: 중심값 기준 ±2단계 (허용 목록 내에서만)
        - trail_start_r: 중심값 기준 ±30%, 9개 포인트
        - trail_dist_r: 중심값 기준 ±25%, 7개 포인트
        - atr_mult: 중심값 기준 ±15%, 5개 포인트
        - entry_validity_hours: Stage 1 최적값 고정

        Args:
            coarse_optimal: Stage 1 최적 파라미터

        Returns:
            Fine-tuning 범위 딕셔너리 (~1,575개 조합)
        """
        import numpy as np

        # filter_tf (전후 2단계, 검증)
        weight = PARAMETER_SENSITIVITY_WEIGHTS['filter_tf']
        tf_map = weight['timeframe_order']
        tf_idx = tf_map.index(coarse_optimal['filter_tf'])

        tf_range = []
        for i in range(-2, 3):
            idx = tf_idx + i
            if 0 <= idx < len(tf_map):
                tf = tf_map[idx]
                if tf in ALLOWED_FILTER_TF:
                    tf_range.append(tf)

        if not tf_range:
            tf_range = [coarse_optimal['filter_tf']]

        # trail_start_r (±30%, 9개)
        ts_weight = PARAMETER_SENSITIVITY_WEIGHTS['trail_start_r']
        ts_center = coarse_optimal['trail_start_r']
        ts_min = max(ts_weight['min_value'], ts_center * 0.7)
        ts_max = min(ts_weight['max_value'], ts_center * 1.3)
        ts_range = self._linspace_n(ts_min, ts_max, ts_weight['n_points'])

        # trail_dist_r (±25%, 7개)
        td_weight = PARAMETER_SENSITIVITY_WEIGHTS['trail_dist_r']
        td_center = coarse_optimal['trail_dist_r']
        td_min = max(td_weight['min_value'], td_center * 0.75)
        td_max = min(td_weight['max_value'], td_center * 1.25)
        td_range = self._linspace_n(td_min, td_max, td_weight['n_points'])

        # atr_mult (±15%, 5개)
        atr_weight = PARAMETER_SENSITIVITY_WEIGHTS['atr_mult']
        atr_center = coarse_optimal['atr_mult']
        atr_min = max(atr_weight['min_value'], atr_center * 0.85)
        atr_max = min(atr_weight['max_value'], atr_center * 1.15)
        atr_range = self._linspace_n(atr_min, atr_max, atr_weight['n_points'])

        return {
            'filter_tf': tf_range,
            'trail_start_r': ts_range,
            'trail_dist_r': td_range,
            'atr_mult': atr_range,
            'entry_validity_hours': [coarse_optimal['entry_validity_hours']]
        }

    @staticmethod
    def _linspace_n(min_val: float, max_val: float, n: int) -> List[float]:
        """N개 균등 분할 (소수점 3자리)"""
        if n == 1:
            return [round((min_val + max_val) / 2, 3)]
        step = (max_val - min_val) / (n - 1)
        return [round(min_val + i * step, 3) for i in range(n)]

    def validate_param_interaction(self, params: dict) -> bool:
        """파라미터 상호작용 검증

        규칙:
        1. atr_mult × trail_start_r ∈ [0.5, 2.5]
        2. filter_tf vs entry_validity_hours 조화
        3. trail_start_r / trail_dist_r ∈ [3.0, 20.0]

        Args:
            params: 검증할 파라미터 딕셔너리

        Returns:
            True: 유효 조합, False: 불조화 조합
        """
        # Rule 1
        interaction_1 = params['atr_mult'] * params['trail_start_r']
        if not (0.5 <= interaction_1 <= 2.5):
            return False

        # Rule 2
        if params['filter_tf'] == '12h' and params['entry_validity_hours'] > 24:
            return False
        if params['filter_tf'] == '1d' and params['entry_validity_hours'] > 48:
            return False

        # Rule 3
        if params['trail_dist_r'] > 0:
            ratio = params['trail_start_r'] / params['trail_dist_r']
            if not (3.0 <= ratio <= 20.0):
                return False

        return True

    def run_stage_1(self, n_cores: int = 8) -> List[OptimizationResult]:
        """Stage 1: Coarse Grid 병렬 실행

        Args:
            n_cores: 워커 수

        Returns:
            결과 리스트 (Sharpe 정렬)
        """
        coarse_ranges = self.build_coarse_ranges()

        # 조합 생성 + 검증
        keys = list(coarse_ranges.keys())
        values = [coarse_ranges[k] for k in keys]
        combos_raw = list(product(*values))

        valid_combos = []
        filtered_count = 0

        for combo in combos_raw:
            params_dict = dict(zip(keys, combo))
            if self.validate_param_interaction(params_dict):
                valid_combos.append(params_dict)
            else:
                filtered_count += 1

        total_raw = len(combos_raw)
        total_valid = len(valid_combos)
        filter_pct = (filtered_count / total_raw * 100) if total_raw > 0 else 0

        logger.info(f"\nStage 1: Coarse Grid")
        logger.info(f"   전체 조합: {total_raw}개")
        logger.info(f"   필터 제거: {filtered_count}개 ({filter_pct:.1f}%)")
        logger.info(f"   유효 조합: {total_valid}개")
        logger.info(f"   파라미터: {', '.join(keys)}")

        # 병렬 백테스트 실행
        results = []
        completed = 0

        with ProcessPoolExecutor(max_workers=n_cores) as executor:
            # 각 조합에 대한 task 생성
            futures = []
            for params_dict in valid_combos:
                full_params = {**self.baseline_params, **params_dict}
                task = (self.strategy_class, full_params, self.df, self.df, TOTAL_COST, 0.0)
                futures.append(executor.submit(_worker_run_single, *task))

            # 결과 수집
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.debug(f"Backtest failed: {e}")

                completed += 1
                if completed % 50 == 0 or completed == total_valid:
                    logger.info(f"   진행: {completed}/{total_valid} ({completed/total_valid*100:.0f}%)")

        # Sharpe 기준 정렬
        results.sort(key=lambda x: x.sharpe_ratio, reverse=True)

        logger.info(f"\nStage 1 완료: {len(results)}개 결과")
        logger.info(f"\n상위 5개:")
        for i, r in enumerate(results[:5], 1):
            logger.info(f"  {i}. Sharpe={r.sharpe_ratio:.2f}, 승률={r.win_rate:.1f}%, "
                       f"MDD={abs(r.max_drawdown):.1f}%, 거래={r.trades}")

        return results

    def run_stage_2(
        self,
        top_5: List[OptimizationResult],
        n_cores: int = 8
    ) -> List[OptimizationResult]:
        """Stage 2: Fine-Tuning 병렬 실행

        Args:
            top_5: Stage 1 상위 5개 결과
            n_cores: 워커 수

        Returns:
            전체 결과 리스트 (Sharpe 정렬)
        """
        all_results = []

        logger.info(f"\nStage 2: Fine-Tuning (상위 5개 영역)")

        for region_idx, coarse_result in enumerate(top_5, 1):
            fine_ranges = self.build_fine_ranges(coarse_result.params)

            # 조합 생성 + 검증
            keys = list(fine_ranges.keys())
            values = [fine_ranges[k] for k in keys]
            combos_raw = list(product(*values))

            valid_combos = []
            filtered_count = 0

            for combo in combos_raw:
                params_dict = dict(zip(keys, combo))
                if self.validate_param_interaction(params_dict):
                    valid_combos.append(params_dict)
                else:
                    filtered_count += 1

            region_total = len(valid_combos)
            logger.info(f"\n영역 {region_idx}/5: {region_total}개 조합 (필터: {filtered_count}개 제거)")

            # 병렬 백테스트 실행
            region_results = []
            completed = 0

            with ProcessPoolExecutor(max_workers=n_cores) as executor:
                # 각 조합에 대한 task 생성
                futures = []
                for params_dict in valid_combos:
                    full_params = {**self.baseline_params, **params_dict}
                    task = (self.strategy_class, full_params, self.df, self.df, TOTAL_COST, 0.0)
                    futures.append(executor.submit(_worker_run_single, *task))

                # 결과 수집
                for future in as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            region_results.append(result)
                    except Exception as e:
                        logger.debug(f"Backtest failed: {e}")

                    completed += 1
                    if completed % 50 == 0 or completed == region_total:
                        logger.info(f"   진행: {completed}/{region_total} ({completed/region_total*100:.0f}%)")

            all_results.extend(region_results)
            logger.info(f"  영역 {region_idx} 완료: {len(region_results)}개 결과")

        # Sharpe 기준 정렬
        all_results.sort(key=lambda x: x.sharpe_ratio, reverse=True)

        logger.info(f"\nStage 2 완료: 총 {len(all_results)}개 결과")

        return all_results

    def save_results(
        self,
        results: List[OptimizationResult],
        output_dir: str = "results"
    ) -> str:
        """결과 CSV 저장

        Args:
            results: 백테스트 결과 리스트
            output_dir: 저장 디렉토리

        Returns:
            저장된 파일 경로
        """
        Path(output_dir).mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"{output_dir}/coarse_fine_results_{timestamp}.csv"

        # CSV 변환
        rows = []
        for r in results:
            row = {
                'sharpe': r.sharpe_ratio,
                'win_rate': r.win_rate,
                'mdd': abs(r.max_drawdown),
                'pnl': r.total_return,
                'trades': r.trades,
                'pf': r.profit_factor,
                'stability': r.grade,
            }
            row.update(r.params)
            rows.append(row)

        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')

        logger.info(f"\n결과 저장: {filepath}")
        return filepath

    def run(
        self,
        n_cores: int = 8,
        save_csv: bool = True
    ) -> CoarseFineResult:
        """2단계 최적화 실행

        Args:
            n_cores: 워커 수
            save_csv: CSV 저장 여부

        Returns:
            CoarseFineResult 객체
        """
        start_time = datetime.now()

        # Stage 1: Coarse Grid
        logger.info("=" * 100)
        logger.info("2단계 Coarse-to-Fine 백테스트 - v7.28")
        logger.info(f"   비용: TOTAL_COST = {TOTAL_COST:.4f} (SSOT)")
        logger.info("=" * 100)

        stage1_results = self.run_stage_1(n_cores)

        if len(stage1_results) < 5:
            logger.warning(f"Stage 1 결과가 5개 미만입니다 ({len(stage1_results)}개)")
            top_5 = stage1_results
        else:
            top_5 = stage1_results[:5]

        # Stage 2: Fine-Tuning
        stage2_results = self.run_stage_2(top_5, n_cores)

        elapsed_seconds = (datetime.now() - start_time).total_seconds()

        # 결과 저장
        csv_path = None
        if save_csv:
            csv_path = self.save_results(stage2_results)

        # 최적 결과
        if stage2_results:
            best = stage2_results[0]
            best_params = best.params
            best_metrics = {
                'sharpe': best.sharpe_ratio,
                'win_rate': best.win_rate,
                'mdd': abs(best.max_drawdown),
                'pnl': best.total_return,
                'trades': best.trades,
                'pf': best.profit_factor,
                'stability': best.grade,
            }
        else:
            best_params = {}
            best_metrics = {}

        return CoarseFineResult(
            stage1_results=stage1_results,
            stage2_results=stage2_results,
            best_params=best_params,
            best_metrics=best_metrics,
            total_combinations=len(stage1_results) + len(stage2_results),
            elapsed_seconds=elapsed_seconds,
            csv_path=csv_path
        )
