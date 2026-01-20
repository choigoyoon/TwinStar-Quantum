"""
tests/test_coarse_to_fine_optimizer.py
Coarse-to-Fine Optimizer 단위 테스트 (v7.28)

Author: Claude Sonnet 4.5
Date: 2026-01-20
"""

import pytest
import pandas as pd
import numpy as np
from pathlib import Path

from core.coarse_to_fine_optimizer import CoarseToFineOptimizer


@pytest.fixture
def sample_df():
    """테스트용 샘플 DataFrame 생성"""
    dates = pd.date_range(start='2020-01-01', periods=1000, freq='1h')
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 50000 + np.random.randn(1000) * 1000,
        'high': 51000 + np.random.randn(1000) * 1000,
        'low': 49000 + np.random.randn(1000) * 1000,
        'close': 50000 + np.random.randn(1000) * 1000,
        'volume': np.random.randint(100, 1000, 1000)
    })
    return df


class TestCoarseToFineOptimizer:
    """CoarseToFineOptimizer 테스트"""

    def test_init(self, sample_df):
        """초기화 테스트"""
        optimizer = CoarseToFineOptimizer(sample_df)

        assert optimizer.df is not None
        assert len(optimizer.df) == 1000
        assert optimizer.strategy_type == 'macd'
        assert optimizer.baseline_params is not None

    def test_build_coarse_ranges(self, sample_df):
        """Coarse Grid 범위 생성 테스트"""
        optimizer = CoarseToFineOptimizer(sample_df)
        ranges = optimizer.build_coarse_ranges()

        # 5개 파라미터 확인
        assert len(ranges) == 5
        assert 'atr_mult' in ranges
        assert 'filter_tf' in ranges
        assert 'entry_validity_hours' in ranges
        assert 'trail_start_r' in ranges
        assert 'trail_dist_r' in ranges

        # atr_mult 범위 확인
        assert len(ranges['atr_mult']) == 4
        assert 0.9 in ranges['atr_mult']
        assert 1.25 in ranges['atr_mult']

        # filter_tf 범위 확인
        assert len(ranges['filter_tf']) == 4
        assert '4h' in ranges['filter_tf']
        assert '12h' in ranges['filter_tf']

        # 전체 조합 수: 4 × 4 × 2 × 4 × 4 = 512
        total_combos = (
            len(ranges['atr_mult']) *
            len(ranges['filter_tf']) *
            len(ranges['entry_validity_hours']) *
            len(ranges['trail_start_r']) *
            len(ranges['trail_dist_r'])
        )
        assert total_combos == 512

    def test_build_fine_ranges(self, sample_df):
        """Fine-Tuning 범위 생성 테스트"""
        optimizer = CoarseToFineOptimizer(sample_df)

        coarse_optimal = {
            'atr_mult': 1.0,
            'filter_tf': '6h',
            'entry_validity_hours': 48,
            'trail_start_r': 0.6,
            'trail_dist_r': 0.05
        }

        ranges = optimizer.build_fine_ranges(coarse_optimal)

        # 5개 파라미터 확인
        assert len(ranges) == 5

        # entry_validity_hours는 고정값 (1개)
        assert len(ranges['entry_validity_hours']) == 1
        assert ranges['entry_validity_hours'][0] == 48

        # filter_tf는 ±2단계 (최대 5개)
        assert len(ranges['filter_tf']) >= 1
        assert '6h' in ranges['filter_tf']

        # trail_start_r는 9개 포인트
        assert len(ranges['trail_start_r']) == 9

        # trail_dist_r는 7개 포인트
        assert len(ranges['trail_dist_r']) == 7

        # atr_mult는 5개 포인트
        assert len(ranges['atr_mult']) == 5

    def test_linspace_n(self, sample_df):
        """_linspace_n 헬퍼 함수 테스트"""
        optimizer = CoarseToFineOptimizer(sample_df)

        # 1개
        result = optimizer._linspace_n(1.0, 2.0, 1)
        assert len(result) == 1
        assert result[0] == 1.5

        # 5개
        result = optimizer._linspace_n(1.0, 2.0, 5)
        assert len(result) == 5
        assert result[0] == 1.0
        assert result[-1] == 2.0
        assert abs(result[2] - 1.5) < 0.01

    def test_validate_param_interaction_valid(self, sample_df):
        """파라미터 검증 테스트 - 유효한 조합"""
        optimizer = CoarseToFineOptimizer(sample_df)

        # Rule 1: atr_mult × trail_start_r ∈ [0.5, 2.5]
        params1 = {
            'atr_mult': 1.0,
            'trail_start_r': 1.0,
            'filter_tf': '6h',
            'entry_validity_hours': 48,
            'trail_dist_r': 0.1
        }
        assert optimizer.validate_param_interaction(params1) is True

        # Rule 2: filter_tf='12h', entry_validity_hours=24 (OK)
        params2 = {
            'atr_mult': 1.0,
            'trail_start_r': 0.8,
            'filter_tf': '12h',
            'entry_validity_hours': 24,
            'trail_dist_r': 0.05
        }
        assert optimizer.validate_param_interaction(params2) is True

        # Rule 3: trail_start_r / trail_dist_r = 10 (OK)
        params3 = {
            'atr_mult': 1.0,
            'trail_start_r': 0.5,
            'filter_tf': '6h',
            'entry_validity_hours': 48,
            'trail_dist_r': 0.05
        }
        assert optimizer.validate_param_interaction(params3) is True

    def test_validate_param_interaction_invalid(self, sample_df):
        """파라미터 검증 테스트 - 무효한 조합"""
        optimizer = CoarseToFineOptimizer(sample_df)

        # Rule 1 위반: 3.0 × 1.0 = 3.0 > 2.5
        params1 = {
            'atr_mult': 3.0,
            'trail_start_r': 1.0,
            'filter_tf': '6h',
            'entry_validity_hours': 48,
            'trail_dist_r': 0.1
        }
        assert optimizer.validate_param_interaction(params1) is False

        # Rule 2 위반: filter_tf='12h', entry_validity_hours=48 > 24
        params2 = {
            'atr_mult': 1.0,
            'trail_start_r': 0.8,
            'filter_tf': '12h',
            'entry_validity_hours': 48,
            'trail_dist_r': 0.05
        }
        assert optimizer.validate_param_interaction(params2) is False

        # Rule 3 위반: 0.5 / 0.2 = 2.5 < 3.0
        params3 = {
            'atr_mult': 1.0,
            'trail_start_r': 0.5,
            'filter_tf': '6h',
            'entry_validity_hours': 48,
            'trail_dist_r': 0.2
        }
        assert optimizer.validate_param_interaction(params3) is False

    def test_save_results(self, sample_df, tmp_path):
        """결과 저장 테스트"""
        from core.optimizer import OptimizationResult

        optimizer = CoarseToFineOptimizer(sample_df)

        # 샘플 결과 생성
        results = [
            OptimizationResult(
                params={'atr_mult': 1.0, 'filter_tf': '6h'},
                sharpe_ratio=15.0,
                win_rate=80.0,
                max_drawdown=-5.0,
                total_return=100.0,
                trades=100,
                profit_factor=3.0,
                grade='A'
            )
        ]

        # 임시 디렉토리에 저장
        filepath = optimizer.save_results(results, output_dir=str(tmp_path))

        # 파일 존재 확인
        assert Path(filepath).exists()

        # CSV 내용 확인
        df = pd.read_csv(filepath)
        assert len(df) == 1
        assert 'sharpe' in df.columns
        assert 'win_rate' in df.columns
        assert 'atr_mult' in df.columns
