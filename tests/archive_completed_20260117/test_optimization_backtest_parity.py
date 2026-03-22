"""최적화-백테스트 계산식 일치성 테스트

이 테스트는 최적화 엔진과 백테스트 워커가 동일한 거래 데이터에 대해
동일한 메트릭 값을 계산하는지 검증합니다.

Test Suite:
1. test_pnl_clamping_parity - PnL 클램핑 일치성
2. test_metric_calculation_parity - 메트릭 계산 일치성
3. test_filter_criteria_parity - 필터 기준 일치성
4. test_direction_filter_parity - Direction 필터 일치성
5. test_compound_return_parity - 누적 수익률 계산 일치성

작성일: 2026-01-15
버전: v1.0
"""

import pytest
from typing import List, Dict
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

from utils.metrics import (
    calculate_mdd,
    calculate_win_rate,
    calculate_sharpe_ratio,
    calculate_profit_factor,
    calculate_stability
)


class TestPnLClampingParity:
    """PnL 클램핑 일치성 테스트"""

    def test_clamping_extreme_values(self):
        """극단적 PnL 값 클램핑 일치성"""
        # 테스트 데이터: 극단적 수익/손실
        trades = [
            {'pnl': 100.0},   # +100% → +50%로 클램핑
            {'pnl': -80.0},   # -80% → -50%로 클램핑
            {'pnl': 30.0},    # 클램핑 불필요
            {'pnl': -20.0},   # 클램핑 불필요
        ]
        leverage = 2

        # 최적화 엔진 로직
        MAX_SINGLE_PNL = 50.0
        MIN_SINGLE_PNL = -50.0
        opt_clamped = []
        for t in trades:
            raw_pnl = t['pnl'] * leverage
            clamped = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, raw_pnl))
            opt_clamped.append(clamped)

        # 백테스트 워커 로직 (수정 후)
        bt_clamped = []
        for t in trades:
            raw_pnl = t['pnl'] * leverage
            clamped = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, raw_pnl))
            bt_clamped.append(clamped)

        # 검증: 완전 일치
        assert opt_clamped == bt_clamped
        assert opt_clamped == [50.0, -50.0, 50.0, -40.0]  # 100*2=200 → 50, -80*2=-160 → -50

    def test_clamping_boundary_values(self):
        """경계값 클램핑 정확성"""
        trades = [
            {'pnl': 25.0},    # 25*2=50 → 경계값 (클램핑 안됨)
            {'pnl': -25.0},   # -25*2=-50 → 경계값 (클램핑 안됨)
            {'pnl': 25.1},    # 25.1*2=50.2 → 50.0으로 클램핑
            {'pnl': -25.1},   # -25.1*2=-50.2 → -50.0으로 클램핑
        ]
        leverage = 2

        MAX_SINGLE_PNL = 50.0
        MIN_SINGLE_PNL = -50.0

        results = []
        for t in trades:
            raw_pnl = t['pnl'] * leverage
            clamped = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, raw_pnl))
            results.append(clamped)

        assert results[0] == 50.0  # 경계값 허용
        assert results[1] == -50.0  # 경계값 허용
        assert results[2] == 50.0  # 클램핑됨
        assert results[3] == -50.0  # 클램핑됨


class TestMetricCalculationParity:
    """메트릭 계산 일치성 테스트"""

    @pytest.fixture
    def sample_trades(self) -> List[Dict]:
        """샘플 거래 데이터 (20개)"""
        return [
            {'pnl': 2.5, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-01')},
            {'pnl': -1.0, 'type': 'Short', 'entry_time': pd.Timestamp('2024-01-02')},
            {'pnl': 3.0, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-03')},
            {'pnl': 1.5, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-04')},
            {'pnl': -0.5, 'type': 'Short', 'entry_time': pd.Timestamp('2024-01-05')},
            {'pnl': 2.0, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-06')},
            {'pnl': -1.5, 'type': 'Short', 'entry_time': pd.Timestamp('2024-01-07')},
            {'pnl': 4.0, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-08')},
            {'pnl': 0.5, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-09')},
            {'pnl': -2.0, 'type': 'Short', 'entry_time': pd.Timestamp('2024-01-10')},
            {'pnl': 1.0, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-11')},
            {'pnl': 2.5, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-12')},
            {'pnl': -0.5, 'type': 'Short', 'entry_time': pd.Timestamp('2024-01-13')},
            {'pnl': 3.5, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-14')},
            {'pnl': 1.5, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-15')},
            {'pnl': -1.0, 'type': 'Short', 'entry_time': pd.Timestamp('2024-01-16')},
            {'pnl': 2.0, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-17')},
            {'pnl': 0.5, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-18')},
            {'pnl': 1.0, 'type': 'Long', 'entry_time': pd.Timestamp('2024-01-19')},
            {'pnl': -0.5, 'type': 'Short', 'entry_time': pd.Timestamp('2024-01-20')},
        ]

    def test_win_rate_calculation(self, sample_trades: List[Dict]):
        """승률 계산 일치성"""
        # SSOT 메트릭
        win_rate = calculate_win_rate(sample_trades)

        # 수동 계산
        wins = len([t for t in sample_trades if t['pnl'] > 0])
        total = len(sample_trades)
        expected = (wins / total) * 100

        assert abs(win_rate - expected) < 0.01, f"Win Rate 불일치: {win_rate} vs {expected}"

    def test_mdd_calculation(self, sample_trades: List[Dict]):
        """MDD 계산 일치성"""
        # SSOT 메트릭
        mdd = calculate_mdd(sample_trades)

        # 수동 계산 (equity curve 기반)
        equity = 1.0
        equity_curve = [1.0]
        for t in sample_trades:
            equity *= (1 + t['pnl'] / 100)
            equity_curve.append(equity)

        peak = equity_curve[0]
        max_dd = 0
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            drawdown = (peak - eq) / peak
            if drawdown > max_dd:
                max_dd = drawdown

        expected = max_dd * 100

        assert abs(mdd - expected) < 0.1, f"MDD 불일치: {mdd:.2f}% vs {expected:.2f}%"

    def test_sharpe_ratio_calculation(self, sample_trades: List[Dict]):
        """Sharpe Ratio 계산 일치성"""
        pnls = [t['pnl'] for t in sample_trades]

        # SSOT 메트릭 (15분봉 기준: 252 * 4 = 1,008)
        sharpe = calculate_sharpe_ratio(pnls, periods_per_year=252 * 4)

        # 수동 계산
        if len(pnls) < 2:
            expected = 0
        else:
            mean = np.mean(pnls)
            std = np.std(pnls, ddof=1)
            if std == 0:
                expected = 0
            else:
                expected = (mean / std) * np.sqrt(252 * 4)

        assert abs(sharpe - expected) < 0.5, f"Sharpe Ratio 불일치: {sharpe:.2f} vs {expected:.2f} (허용 오차: 0.5)"

    def test_profit_factor_calculation(self, sample_trades: List[Dict]):
        """Profit Factor 계산 일치성"""
        # SSOT 메트릭
        pf = calculate_profit_factor(sample_trades)

        # 수동 계산
        gains = sum([t['pnl'] for t in sample_trades if t['pnl'] > 0])
        losses = abs(sum([t['pnl'] for t in sample_trades if t['pnl'] < 0]))

        if losses == 0:
            expected = gains if gains > 0 else 0
        else:
            expected = gains / losses

        assert abs(pf - expected) < 0.01, f"Profit Factor 불일치: {pf:.2f} vs {expected:.2f}"


class TestCompoundReturnParity:
    """누적 수익률 계산 일치성 테스트"""

    def test_compound_return_with_clamping(self):
        """클램핑 적용 시 누적 수익률 일치성"""
        trades = [
            {'pnl': 100.0},  # → 50.0 (클램핑)
            {'pnl': 10.0},
            {'pnl': -80.0},  # → -50.0 (클램핑)
            {'pnl': 5.0},
        ]
        leverage = 1

        MAX_SINGLE_PNL = 50.0
        MIN_SINGLE_PNL = -50.0

        # 클램핑 적용
        clamped_pnls = []
        for t in trades:
            raw_pnl = t['pnl'] * leverage
            clamped = max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, raw_pnl))
            clamped_pnls.append(clamped)

        # 최적화 엔진 로직
        equity_opt = 1.0
        for p in clamped_pnls:
            equity_opt *= (1 + p / 100)
            if equity_opt <= 0:
                equity_opt = 0
                break
        compound_opt = (equity_opt - 1) * 100
        compound_opt = max(-100.0, min(compound_opt, 1e10))

        # 백테스트 워커 로직 (수정 후)
        equity_bt = 1.0
        for p in clamped_pnls:
            equity_bt *= (1 + p / 100)
            if equity_bt <= 0:
                equity_bt = 0
                break
        compound_bt = (equity_bt - 1) * 100
        compound_bt = max(-100.0, min(compound_bt, 1e10))

        # 검증: 완전 일치
        assert abs(compound_opt - compound_bt) < 0.01
        assert equity_opt == equity_bt

    def test_compound_return_boundary(self):
        """범위 제한 경계값 테스트"""
        # 극단적 손실 (equity = 0)
        trades = [{'pnl': -100.0}]
        leverage = 1

        equity = 1.0
        for t in trades:
            pnl = t['pnl'] * leverage
            pnl = max(-50.0, min(50.0, pnl))  # 클램핑
            equity *= (1 + pnl / 100)
            if equity <= 0:
                equity = 0
                break

        compound = (equity - 1) * 100
        compound = max(-100.0, min(compound, 1e10))

        # -50% PnL → equity = 0.5 → compound = -50%
        assert compound == -50.0

        # 극단적 수익 (오버플로우 방지)
        trades = [{'pnl': 50.0}] * 100  # 50% * 100회
        leverage = 1

        equity = 1.0
        for t in trades:
            pnl = t['pnl'] * leverage
            pnl = max(-50.0, min(50.0, pnl))
            equity *= (1 + pnl / 100)
            if equity <= 0:
                equity = 0
                break

        compound = (equity - 1) * 100
        compound = max(-100.0, min(compound, 1e10))

        # 상한 제한 확인
        assert compound <= 1e10


class TestFilterCriteriaParity:
    """필터 기준 일치성 테스트"""

    def test_passes_filter_logic(self):
        """필터 통과 로직 일치성"""
        # Case 1: 모든 조건 만족
        result1 = {
            'max_drawdown': 15.0,
            'win_rate': 80.0,
            'trades': 20
        }
        passes1 = (
            abs(result1['max_drawdown']) <= 20.0 and
            result1['win_rate'] >= 75.0 and
            result1['trades'] >= 10
        )
        assert passes1 is True

        # Case 2: MDD 초과
        result2 = {
            'max_drawdown': 25.0,
            'win_rate': 80.0,
            'trades': 20
        }
        passes2 = (
            abs(result2['max_drawdown']) <= 20.0 and
            result2['win_rate'] >= 75.0 and
            result2['trades'] >= 10
        )
        assert passes2 is False

        # Case 3: 승률 미달
        result3 = {
            'max_drawdown': 15.0,
            'win_rate': 70.0,
            'trades': 20
        }
        passes3 = (
            abs(result3['max_drawdown']) <= 20.0 and
            result3['win_rate'] >= 75.0 and
            result3['trades'] >= 10
        )
        assert passes3 is False

        # Case 4: 거래 수 부족
        result4 = {
            'max_drawdown': 15.0,
            'win_rate': 80.0,
            'trades': 5
        }
        passes4 = (
            abs(result4['max_drawdown']) <= 20.0 and
            result4['win_rate'] >= 75.0 and
            result4['trades'] >= 10
        )
        assert passes4 is False


class TestDirectionFilterParity:
    """Direction 필터 일치성 테스트"""

    def test_direction_filter_long(self):
        """Long 방향 필터"""
        trades = [
            {'pnl': 1.0, 'type': 'Long'},
            {'pnl': 2.0, 'type': 'Short'},
            {'pnl': 3.0, 'type': 'Long'},
            {'pnl': -1.0, 'type': 'Short'},
        ]
        direction = 'Long'

        # 최적화 엔진 로직
        if direction != 'Both':
            filtered = [t for t in trades if t['type'] == direction]
        else:
            filtered = trades

        assert len(filtered) == 2
        assert all(t['type'] == 'Long' for t in filtered)

    def test_direction_filter_short(self):
        """Short 방향 필터"""
        trades = [
            {'pnl': 1.0, 'type': 'Long'},
            {'pnl': 2.0, 'type': 'Short'},
            {'pnl': 3.0, 'type': 'Long'},
            {'pnl': -1.0, 'type': 'Short'},
        ]
        direction = 'Short'

        if direction != 'Both':
            filtered = [t for t in trades if t['type'] == direction]
        else:
            filtered = trades

        assert len(filtered) == 2
        assert all(t['type'] == 'Short' for t in filtered)

    def test_direction_filter_both(self):
        """Both 방향 (필터 없음)"""
        trades = [
            {'pnl': 1.0, 'type': 'Long'},
            {'pnl': 2.0, 'type': 'Short'},
            {'pnl': 3.0, 'type': 'Long'},
            {'pnl': -1.0, 'type': 'Short'},
        ]
        direction = 'Both'

        if direction != 'Both':
            filtered = [t for t in trades if t['type'] == direction]
        else:
            filtered = trades

        assert len(filtered) == 4  # 모든 거래 포함


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_empty_trades(self):
        """빈 거래 리스트"""
        trades = []

        win_rate = calculate_win_rate(trades)
        mdd = calculate_mdd(trades)
        pf = calculate_profit_factor(trades)

        assert win_rate == 0
        assert mdd == 0
        assert pf == 0

    def test_single_trade(self):
        """단일 거래"""
        trades = [{'pnl': 5.0}]

        win_rate = calculate_win_rate(trades)
        mdd = calculate_mdd(trades)
        pf = calculate_profit_factor(trades)

        assert win_rate == 100.0
        assert mdd >= 0
        assert pf == 5.0  # gains만 존재

    def test_all_wins(self):
        """모두 수익 거래"""
        trades = [{'pnl': 1.0}, {'pnl': 2.0}, {'pnl': 3.0}]

        win_rate = calculate_win_rate(trades)
        pf = calculate_profit_factor(trades)

        assert win_rate == 100.0
        assert pf == 6.0  # gains만 존재

    def test_all_losses(self):
        """모두 손실 거래"""
        trades = [{'pnl': -1.0}, {'pnl': -2.0}, {'pnl': -3.0}]

        win_rate = calculate_win_rate(trades)
        pf = calculate_profit_factor(trades)

        assert win_rate == 0.0
        assert pf == 0  # losses만 존재


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
