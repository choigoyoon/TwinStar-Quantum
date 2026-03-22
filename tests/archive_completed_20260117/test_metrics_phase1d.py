"""Phase 1-D 메트릭 통합 테스트"""
import pytest
import pandas as pd
from utils.metrics import (
    calculate_backtest_metrics,
    calculate_stability,
    calculate_cagr,
    calculate_avg_trades_per_day,
    calculate_optimal_leverage,
)


class TestLeverageApplication:
    """Leverage 적용 통일 테스트"""

    def test_leverage_5x(self):
        """leverage=5 적용 테스트"""
        trades = [{'pnl': 10}, {'pnl': -5}]
        metrics = calculate_backtest_metrics(trades, leverage=5)

        # 기대값: (10*5) + (-5*5) = 25
        assert metrics['total_pnl'] == 25

    def test_leverage_default(self):
        """leverage=1 (기본값) 테스트"""
        trades = [{'pnl': 10}, {'pnl': -5}]
        metrics = calculate_backtest_metrics(trades, leverage=1)

        # 기대값: 10 + (-5) = 5
        assert metrics['total_pnl'] == 5

    def test_leverage_10x(self):
        """leverage=10 적용 테스트"""
        trades = [{'pnl': 5}, {'pnl': 3}, {'pnl': -2}]
        metrics = calculate_backtest_metrics(trades, leverage=10)

        # 기대값: (5*10) + (3*10) + (-2*10) = 60
        assert metrics['total_pnl'] == 60


class TestStability:
    """Stability 함수 테스트"""

    def test_all_positive(self):
        """3구간 모두 수익"""
        pnls = [10, 5, -2, 8, 3, 12, -1, 4, 6]
        result = calculate_stability(pnls)
        assert result == "✅✅✅"

    def test_insufficient_trades(self):
        """거래 부족 (3개 미만)"""
        pnls = [10, -5]
        result = calculate_stability(pnls)
        assert result == "⚠️"

    def test_two_positive_sections(self):
        """2구간 수익"""
        pnls = [10, 5, 3, -6, -8, -2, 12, 3, 4]  # 1구간+, 2구간-, 3구간+
        result = calculate_stability(pnls)
        assert result == "✅✅⚠"

    def test_one_positive_section(self):
        """1구간만 수익"""
        pnls = [10, 5, 3, -6, -8, -2, -1, -3, -4]  # 1구간+, 2구간-, 3구간-
        result = calculate_stability(pnls)
        assert result == "✅⚠⚠"

    def test_all_negative(self):
        """모든 구간 손실"""
        pnls = [-10, -5, -3, -6, -8, -2, -1, -3, -4]
        result = calculate_stability(pnls)
        assert result == "⚠⚠⚠"


class TestCAGR:
    """CAGR 계산 테스트"""

    def test_one_year_growth(self):
        """1년간 성장률"""
        trades = [
            {'entry_time': pd.Timestamp('2024-01-01'), 'pnl': 10},
            {'entry_time': pd.Timestamp('2025-01-01'), 'pnl': 5},
        ]
        cagr = calculate_cagr(trades, final_capital=115.5, initial_capital=100.0)
        assert abs(cagr - 15.5) < 0.1  # 오차 0.1% 이내

    def test_insufficient_trades(self):
        """거래 부족"""
        trades = [{'entry_time': pd.Timestamp('2024-01-01'), 'pnl': 10}]
        cagr = calculate_cagr(trades, final_capital=110.0)
        assert cagr == 0.0

    def test_no_trades(self):
        """거래 없음"""
        trades = []
        cagr = calculate_cagr(trades, final_capital=100.0)
        assert cagr == 0.0


class TestAvgTradesPerDay:
    """일평균 거래 계산 테스트"""

    def test_three_trades_two_days(self):
        """3거래 / 2일"""
        trades = [
            {'entry_time': pd.Timestamp('2024-01-01')},
            {'entry_time': pd.Timestamp('2024-01-02')},
            {'entry_time': pd.Timestamp('2024-01-03')},
        ]
        avg = calculate_avg_trades_per_day(trades)
        assert avg == 1.5  # 3거래 / 2일

    def test_insufficient_trades(self):
        """거래 부족"""
        trades = [{'entry_time': pd.Timestamp('2024-01-01')}]
        avg = calculate_avg_trades_per_day(trades)
        assert avg == 0.0

    def test_ten_days(self):
        """10일간 5거래"""
        trades = [
            {'entry_time': pd.Timestamp('2024-01-01')},
            {'entry_time': pd.Timestamp('2024-01-03')},
            {'entry_time': pd.Timestamp('2024-01-05')},
            {'entry_time': pd.Timestamp('2024-01-08')},
            {'entry_time': pd.Timestamp('2024-01-11')},
        ]
        avg = calculate_avg_trades_per_day(trades)
        assert avg == 0.5  # 5거래 / 10일


class TestOptimalLeverage:
    """적정 레버리지 계산 테스트"""

    def test_mdd_40_target_20(self):
        """MDD 40% → target 20%"""
        leverage = calculate_optimal_leverage(mdd=40.0, target_mdd=20.0)
        assert leverage == 1  # 40% MDD는 줄여야 함 (레버리지 낮춤)

    def test_mdd_10_target_20(self):
        """MDD 10% → target 20%"""
        leverage = calculate_optimal_leverage(mdd=10.0, target_mdd=20.0)
        assert leverage == 2  # 10% MDD → 20% 허용 (레버리지 2배)

    def test_mdd_zero(self):
        """MDD 0%"""
        leverage = calculate_optimal_leverage(mdd=0.0)
        assert leverage == 1

    def test_max_leverage_limit(self):
        """최대 레버리지 제한"""
        leverage = calculate_optimal_leverage(mdd=1.0, target_mdd=20.0, max_leverage=5)
        assert leverage == 5  # 최대값 제한

    def test_mdd_5_target_20(self):
        """MDD 5% → target 20%"""
        leverage = calculate_optimal_leverage(mdd=5.0, target_mdd=20.0)
        assert leverage == 4  # 5% MDD → 20% 허용 (레버리지 4배)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
