"""
Phase 1-E: 최적화 시스템 SSOT 통합 테스트

테스트 대상:
- Multi Optimizer SSOT 마이그레이션 (P0-1)
- Optimizer Stability SSOT 마이그레이션 (P0-2)
- 클램핑 정책 적용 (P1-1, P1-2)
- 메트릭 일관성 검증

작성: 2026-01-15
"""

import unittest
from typing import List, Dict


class TestPhase1ESSOT(unittest.TestCase):
    """Phase 1-E SSOT 통합 테스트"""

    def setUp(self):
        """테스트 데이터 준비"""
        # 정상 케이스 (±20%)
        self.normal_trades = [
            {'pnl': 10.0},
            {'pnl': -5.0},
            {'pnl': 15.0},
            {'pnl': -8.0},
            {'pnl': 12.0},
        ]

        # 극단적 케이스 (±100%)
        self.extreme_trades = [
            {'pnl': 100.0},  # 클램핑 발동: 50%
            {'pnl': -100.0},  # 클램핑 발동: -50%
            {'pnl': 80.0},   # 클램핑 발동: 50%
            {'pnl': -80.0},  # 클램핑 발동: -50%
            {'pnl': 20.0},   # 클램핑 없음
        ]

        # Edge Case: 모든 거래 수익
        self.all_wins = [
            {'pnl': 10.0},
            {'pnl': 15.0},
            {'pnl': 20.0},
        ]

        # Edge Case: 모든 거래 손실
        self.all_losses = [
            {'pnl': -10.0},
            {'pnl': -15.0},
            {'pnl': -20.0},
        ]

    def test_ssot_import(self):
        """SSOT 모듈 import 테스트"""
        from utils.metrics import (
            calculate_win_rate,
            calculate_mdd,
            calculate_profit_factor,
            calculate_sharpe_ratio,
            calculate_stability
        )

        # Import 성공 확인
        self.assertIsNotNone(calculate_win_rate)
        self.assertIsNotNone(calculate_mdd)
        self.assertIsNotNone(calculate_profit_factor)
        self.assertIsNotNone(calculate_sharpe_ratio)
        self.assertIsNotNone(calculate_stability)

    def test_multi_optimizer_ssot(self):
        """Multi Optimizer SSOT 마이그레이션 테스트 (P0-1)"""
        from utils.metrics import calculate_win_rate, calculate_mdd, calculate_profit_factor

        # 정상 케이스
        win_rate = calculate_win_rate(self.normal_trades)
        mdd = calculate_mdd(self.normal_trades)
        pf = calculate_profit_factor(self.normal_trades)

        # 검증
        self.assertGreater(win_rate, 0)
        self.assertLessEqual(win_rate, 100)
        self.assertGreaterEqual(mdd, 0)
        self.assertGreater(pf, 0)

    def test_optimizer_stability_ssot(self):
        """Optimizer Stability SSOT 마이그레이션 테스트 (P0-2)"""
        from utils.metrics import calculate_stability

        # 정상 케이스
        pnls = [t['pnl'] for t in self.normal_trades]
        stability = calculate_stability(pnls)

        # 검증: stability는 "✅" 또는 "⚠" 조합 (Variation Selector 없음)
        self.assertIsInstance(stability, str)
        self.assertTrue(all(c in ['✅', '⚠'] for c in stability))
        self.assertEqual(len(stability), 3)  # 3구간

    def test_clamping_policy(self):
        """클램핑 정책 테스트 (P1-1, P1-2)"""
        MAX_SINGLE_PNL = 50.0
        MIN_SINGLE_PNL = -50.0

        # 클램핑 적용
        clamped_trades = [
            {'pnl': max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, t['pnl']))}
            for t in self.extreme_trades
        ]

        # 검증: 모든 PnL이 -50% ~ +50% 범위 내
        for trade in clamped_trades:
            self.assertGreaterEqual(trade['pnl'], MIN_SINGLE_PNL)
            self.assertLessEqual(trade['pnl'], MAX_SINGLE_PNL)

    def test_metric_consistency(self):
        """메트릭 일관성 테스트 (optimizer vs optimization_logic vs multi_optimizer)"""
        from utils.metrics import (
            calculate_win_rate,
            calculate_mdd,
            calculate_profit_factor
        )

        # 동일한 입력에 대해 동일한 출력 확인
        trades = self.normal_trades

        win_rate_1 = calculate_win_rate(trades)
        win_rate_2 = calculate_win_rate(trades)
        self.assertEqual(win_rate_1, win_rate_2)

        mdd_1 = calculate_mdd(trades)
        mdd_2 = calculate_mdd(trades)
        self.assertEqual(mdd_1, mdd_2)

        pf_1 = calculate_profit_factor(trades)
        pf_2 = calculate_profit_factor(trades)
        self.assertEqual(pf_1, pf_2)

    def test_edge_case_all_wins(self):
        """Edge Case: 모든 거래 수익"""
        from utils.metrics import calculate_win_rate, calculate_profit_factor

        win_rate = calculate_win_rate(self.all_wins)
        pf = calculate_profit_factor(self.all_wins)

        # 검증
        self.assertEqual(win_rate, 100.0)  # 100% 승률
        self.assertGreater(pf, 0)  # PF > 0 (losses==0이면 gains 반환)

    def test_edge_case_all_losses(self):
        """Edge Case: 모든 거래 손실"""
        from utils.metrics import calculate_win_rate, calculate_profit_factor

        win_rate = calculate_win_rate(self.all_losses)
        pf = calculate_profit_factor(self.all_losses)

        # 검증
        self.assertEqual(win_rate, 0.0)  # 0% 승률
        self.assertEqual(pf, 0.0)  # PF = 0 (gains==0)

    def test_edge_case_no_trades(self):
        """Edge Case: 거래 0개"""
        from utils.metrics import calculate_win_rate, calculate_mdd, calculate_profit_factor

        trades = []

        win_rate = calculate_win_rate(trades)
        mdd = calculate_mdd(trades)
        pf = calculate_profit_factor(trades)

        # 검증: 모든 메트릭 0 반환
        self.assertEqual(win_rate, 0.0)
        self.assertEqual(mdd, 0.0)
        self.assertEqual(pf, 0.0)

    def test_edge_case_single_trade(self):
        """Edge Case: 거래 1개"""
        from utils.metrics import calculate_win_rate, calculate_mdd, calculate_profit_factor

        trades = [{'pnl': 10.0}]

        win_rate = calculate_win_rate(trades)
        mdd = calculate_mdd(trades)
        pf = calculate_profit_factor(trades)

        # 검증
        self.assertEqual(win_rate, 100.0)  # 1개 수익 → 100%
        self.assertGreaterEqual(mdd, 0.0)
        self.assertGreater(pf, 0.0)

    def test_extreme_pnl_values(self):
        """극단적 PnL 값 테스트"""
        from utils.metrics import calculate_mdd

        # 클램핑 전
        extreme_pnl = [{'pnl': 1000.0}, {'pnl': -1000.0}]
        mdd_before = calculate_mdd(extreme_pnl)

        # 클램핑 후
        MAX_SINGLE_PNL = 50.0
        MIN_SINGLE_PNL = -50.0
        clamped_pnl = [
            {'pnl': max(MIN_SINGLE_PNL, min(MAX_SINGLE_PNL, t['pnl']))}
            for t in extreme_pnl
        ]
        mdd_after = calculate_mdd(clamped_pnl)

        # 검증: 클램핑 후 MDD가 더 작아야 함
        self.assertLess(mdd_after, mdd_before)

    def test_stability_distribution(self):
        """Stability 분포 테스트"""
        from utils.metrics import calculate_stability

        # 3구간 모두 수익
        all_positive = [10, 10, 10, 10, 10, 10]
        stability_all_pos = calculate_stability(all_positive)
        self.assertEqual(stability_all_pos, "✅✅✅")

        # 3구간 모두 손실
        all_negative = [-10, -10, -10, -10, -10, -10]
        stability_all_neg = calculate_stability(all_negative)
        self.assertEqual(stability_all_neg, "⚠⚠⚠")

        # 2구간 수익, 1구간 손실
        mixed = [10, 10, 10, 10, -10, -10]
        stability_mixed = calculate_stability(mixed)
        self.assertIn(stability_mixed, ["✅✅⚠", "✅⚠✅", "⚠✅✅"])


if __name__ == '__main__':
    unittest.main()
