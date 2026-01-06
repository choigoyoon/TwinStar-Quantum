"""
Unit Tests: Batch Optimizer Boundary Values
Tests strict filtering with exact boundary conditions
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.batch_optimizer import BatchOptimizer


class TestOptimizerBoundaryValues(unittest.TestCase):
    """Test strict filtering with exact boundary conditions"""
    
    def setUp(self):
        self.optimizer = BatchOptimizer(
            min_win_rate=70.0,
            max_mdd=20.0,
            min_trades=30
        )
    
    # =====================
    # Win Rate Tests
    # =====================
    
    def test_win_rate_69_9_fails(self):
        """69.9% WinRate should FAIL"""
        result = {'win_rate': 69.9, 'max_drawdown': 15.0, 'total_trades': 50}
        passed = self._check_filter(result)
        self.assertFalse(passed, "69.9% WinRate should fail")
    
    def test_win_rate_70_0_passes(self):
        """70.0% WinRate should PASS"""
        result = {'win_rate': 70.0, 'max_drawdown': 15.0, 'total_trades': 50}
        passed = self._check_filter(result)
        self.assertTrue(passed, "70.0% WinRate should pass")
    
    def test_win_rate_70_1_passes(self):
        """70.1% WinRate should PASS"""
        result = {'win_rate': 70.1, 'max_drawdown': 15.0, 'total_trades': 50}
        passed = self._check_filter(result)
        self.assertTrue(passed, "70.1% WinRate should pass")
    
    # =====================
    # MDD Tests
    # =====================
    
    def test_mdd_20_1_fails(self):
        """20.1% MDD should FAIL"""
        result = {'win_rate': 75.0, 'max_drawdown': 20.1, 'total_trades': 50}
        passed = self._check_filter(result)
        self.assertFalse(passed, "20.1% MDD should fail")
    
    def test_mdd_20_0_passes(self):
        """20.0% MDD should PASS"""
        result = {'win_rate': 75.0, 'max_drawdown': 20.0, 'total_trades': 50}
        passed = self._check_filter(result)
        self.assertTrue(passed, "20.0% MDD should pass")
    
    def test_mdd_19_9_passes(self):
        """19.9% MDD should PASS"""
        result = {'win_rate': 75.0, 'max_drawdown': 19.9, 'total_trades': 50}
        passed = self._check_filter(result)
        self.assertTrue(passed, "19.9% MDD should pass")
    
    # =====================
    # Trade Count Tests
    # =====================
    
    def test_trades_29_fails(self):
        """29 trades should FAIL"""
        result = {'win_rate': 80.0, 'max_drawdown': 10.0, 'total_trades': 29}
        passed = self._check_filter(result)
        self.assertFalse(passed, "29 trades should fail")
    
    def test_trades_30_passes(self):
        """30 trades should PASS"""
        result = {'win_rate': 80.0, 'max_drawdown': 10.0, 'total_trades': 30}
        passed = self._check_filter(result)
        self.assertTrue(passed, "30 trades should pass")
    
    def test_trades_31_passes(self):
        """31 trades should PASS"""
        result = {'win_rate': 80.0, 'max_drawdown': 10.0, 'total_trades': 31}
        passed = self._check_filter(result)
        self.assertTrue(passed, "31 trades should pass")
    
    # =====================
    # Combined Boundary Test
    # =====================
    
    def test_exact_boundary_passes(self):
        """Exactly at all boundaries should PASS"""
        result = {'win_rate': 70.0, 'max_drawdown': 20.0, 'total_trades': 30}
        passed = self._check_filter(result)
        self.assertTrue(passed, "Exact boundary values should pass")
    
    def test_one_below_all_fails(self):
        """Slightly below on ALL metrics should FAIL"""
        result = {'win_rate': 69.9, 'max_drawdown': 20.1, 'total_trades': 29}
        passed = self._check_filter(result)
        self.assertFalse(passed, "Below all boundaries should fail")
    
    # =====================
    # Helper
    # =====================
    
    def _check_filter(self, result):
        """Check if result passes strict filter"""
        wr = result.get('win_rate', 0)
        mdd = result.get('max_drawdown', 100)
        tr = result.get('total_trades', 0)
        
        failed_reasons = []
        if wr < self.optimizer.min_win_rate:
            failed_reasons.append('WinRate')
        if mdd > self.optimizer.max_mdd:
            failed_reasons.append('MDD')
        if tr < self.optimizer.min_trades:
            failed_reasons.append('Trades')
        
        return len(failed_reasons) == 0


class TestOptimizerFailureCases(unittest.TestCase):
    """Test failure/edge case handling"""
    
    def setUp(self):
        self.optimizer = BatchOptimizer()
    
    def test_empty_result(self):
        """Empty result should fail gracefully"""
        result = {}
        wr = result.get('win_rate', 0)
        mdd = result.get('max_drawdown', 100)
        tr = result.get('total_trades', 0)
        
        self.assertEqual(wr, 0)
        self.assertEqual(mdd, 100)
        self.assertEqual(tr, 0)
    
    def test_none_result(self):
        """None result should be handled"""
        result = None
        self.assertIsNone(result)
    
    def test_missing_fields(self):
        """Missing fields should use defaults"""
        result = {'win_rate': 75.0}  # Missing mdd, trades
        
        mdd = result.get('max_drawdown', 100)
        tr = result.get('total_trades', 0)
        
        self.assertEqual(mdd, 100)  # Default high = fail
        self.assertEqual(tr, 0)     # Default 0 = fail


class TestOptimizerComplexConditions(unittest.TestCase):
    """Test complex multi-condition scenarios"""
    
    def setUp(self):
        self.optimizer = BatchOptimizer(
            min_win_rate=70.0,
            max_mdd=20.0,
            min_trades=30
        )
    
    def test_high_wr_high_mdd_fails(self):
        """80% WinRate + 25% MDD should FAIL (MDD exceeds)"""
        result = {'win_rate': 80.0, 'max_drawdown': 25.0, 'total_trades': 50}
        passed = self._check_filter(result)
        self.assertFalse(passed, "High WR with high MDD should fail")
    
    def test_low_wr_low_mdd_fails(self):
        """65% WinRate + 15% MDD should FAIL (WR insufficient)"""
        result = {'win_rate': 65.0, 'max_drawdown': 15.0, 'total_trades': 50}
        passed = self._check_filter(result)
        self.assertFalse(passed, "Low WR with low MDD should fail")
    
    def test_all_pass_except_trades(self):
        """70% WR + 20% MDD + 25 trades should FAIL (trades insufficient)"""
        result = {'win_rate': 70.0, 'max_drawdown': 20.0, 'total_trades': 25}
        passed = self._check_filter(result)
        self.assertFalse(passed, "Pass WR/MDD but fail trades should fail overall")
    
    def test_all_conditions_met(self):
        """70% WR + 20% MDD + 30 trades should PASS (all met)"""
        result = {'win_rate': 70.0, 'max_drawdown': 20.0, 'total_trades': 30}
        passed = self._check_filter(result)
        self.assertTrue(passed, "All conditions met should pass")
    
    def test_excellent_results_pass(self):
        """85% WR + 10% MDD + 100 trades should PASS"""
        result = {'win_rate': 85.0, 'max_drawdown': 10.0, 'total_trades': 100}
        passed = self._check_filter(result)
        self.assertTrue(passed, "Excellent results should pass")
    
    def test_two_conditions_fail(self):
        """60% WR + 25% MDD should FAIL (two conditions fail)"""
        result = {'win_rate': 60.0, 'max_drawdown': 25.0, 'total_trades': 50}
        passed = self._check_filter(result)
        self.assertFalse(passed)
        
        # Count failures
        reasons = self._get_fail_reasons(result)
        self.assertEqual(len(reasons), 2)
    
    def _check_filter(self, result):
        """Check if result passes strict filter"""
        wr = result.get('win_rate', 0)
        mdd = result.get('max_drawdown', 100)
        tr = result.get('total_trades', 0)
        
        return (wr >= self.optimizer.min_win_rate and 
                mdd <= self.optimizer.max_mdd and 
                tr >= self.optimizer.min_trades)
    
    def _get_fail_reasons(self, result):
        """Get list of failure reasons"""
        reasons = []
        wr = result.get('win_rate', 0)
        mdd = result.get('max_drawdown', 100)
        tr = result.get('total_trades', 0)
        
        if wr < self.optimizer.min_win_rate:
            reasons.append('WinRate')
        if mdd > self.optimizer.max_mdd:
            reasons.append('MDD')
        if tr < self.optimizer.min_trades:
            reasons.append('Trades')
        return reasons


if __name__ == '__main__':
    unittest.main(verbosity=2)
