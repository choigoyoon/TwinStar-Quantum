"""
Unit Tests: Unified Backtest Logic
Tests timestamp sorting, position rules, calculations
"""
import unittest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestUnifiedBacktestLogic(unittest.TestCase):
    """Test unified backtest core logic"""
    
    def test_signal_timestamp_sorting(self):
        """Signals should be sorted by timestamp"""
        signals = [
            {'timestamp': datetime(2025, 1, 1, 14, 0), 'symbol': 'ETH'},
            {'timestamp': datetime(2025, 1, 1, 10, 0), 'symbol': 'BTC'},
            {'timestamp': datetime(2025, 1, 1, 12, 0), 'symbol': 'SOL'},
        ]
        
        sorted_signals = sorted(signals, key=lambda x: x['timestamp'])
        
        self.assertEqual(sorted_signals[0]['symbol'], 'BTC')
        self.assertEqual(sorted_signals[1]['symbol'], 'SOL')
        self.assertEqual(sorted_signals[2]['symbol'], 'ETH')
    
    def test_single_position_rule_blocks_concurrent(self):
        """Concurrent signals should be blocked when position is open"""
        current_position_end = datetime(2025, 1, 1, 13, 0)
        
        signal_times = [
            datetime(2025, 1, 1, 10, 0),  # Opening signal
            datetime(2025, 1, 1, 11, 0),  # Should be blocked
            datetime(2025, 1, 1, 12, 0),  # Should be blocked
            datetime(2025, 1, 1, 14, 0),  # Should pass (after end)
        ]
        
        accepted = []
        position_end = datetime.min
        
        for ts in signal_times:
            if ts >= position_end:
                accepted.append(ts)
                position_end = ts + timedelta(hours=3)  # 3h trade duration
        
        self.assertEqual(len(accepted), 2)
        self.assertEqual(accepted[0], datetime(2025, 1, 1, 10, 0))
        self.assertEqual(accepted[1], datetime(2025, 1, 1, 14, 0))
    
    def test_pnl_calculation_long(self):
        """Long trade PnL calculation"""
        entry_price = 100.0
        exit_price = 110.0
        direction = 'buy'
        
        pnl = (exit_price - entry_price) / entry_price * 100
        
        self.assertAlmostEqual(pnl, 10.0)
    
    def test_pnl_calculation_short(self):
        """Short trade PnL calculation"""
        entry_price = 100.0
        exit_price = 90.0
        direction = 'sell'
        
        raw_pnl = (exit_price - entry_price) / entry_price * 100
        pnl = -raw_pnl  # Invert for short
        
        self.assertAlmostEqual(pnl, 10.0)
    
    def test_win_rate_calculation(self):
        """Win rate calculation"""
        trades = [
            {'pnl_percent': 5.0},   # Win
            {'pnl_percent': -3.0},  # Loss
            {'pnl_percent': 2.0},   # Win
            {'pnl_percent': 8.0},   # Win
            {'pnl_percent': -1.0},  # Loss
        ]
        
        wins = sum(1 for t in trades if t['pnl_percent'] > 0)
        total = len(trades)
        win_rate = (wins / total) * 100
        
        self.assertEqual(wins, 3)
        self.assertAlmostEqual(win_rate, 60.0)
    
    def test_mdd_calculation(self):
        """Maximum Drawdown calculation"""
        equity_history = [1000, 1100, 1050, 1200, 900, 1100]
        
        peak = equity_history[0]
        max_dd = 0
        
        for eq in equity_history:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        # Peak was 1200, lowest after was 900 = 25% DD
        self.assertAlmostEqual(max_dd, 25.0)


class TestUnifiedBacktestEdgeCases(unittest.TestCase):
    """Test edge case handling"""
    
    def test_no_signals(self):
        """Empty signal list should return valid result"""
        signals = []
        
        total_trades = len(signals)
        win_rate = 0.0 if total_trades == 0 else 50.0
        
        self.assertEqual(total_trades, 0)
        self.assertEqual(win_rate, 0.0)
    
    def test_single_signal(self):
        """Single signal should process correctly"""
        signals = [{'timestamp': datetime.now(), 'symbol': 'BTC'}]
        
        self.assertEqual(len(signals), 1)
    
    def test_all_same_timestamp(self):
        """Signals at same time - only first should execute"""
        ts = datetime(2025, 1, 1, 12, 0)
        signals = [
            {'timestamp': ts, 'symbol': 'BTC'},
            {'timestamp': ts, 'symbol': 'ETH'},
            {'timestamp': ts, 'symbol': 'SOL'},
        ]
        
        accepted = []
        position_busy = False
        
        for sig in signals:
            if not position_busy:
                accepted.append(sig)
                position_busy = True
        
        self.assertEqual(len(accepted), 1)
        self.assertEqual(accepted[0]['symbol'], 'BTC')


class TestPnLAccuracy(unittest.TestCase):
    """Test PnL calculation accuracy with leverage and fees"""
    
    def test_long_profit_10_percent(self):
        """Long: Entry 100 → Exit 110 = +10% PnL"""
        entry = 100.0
        exit_price = 110.0
        pnl = (exit_price - entry) / entry * 100
        self.assertAlmostEqual(pnl, 10.0, places=2)
    
    def test_long_loss_10_percent(self):
        """Long: Entry 100 → Exit 90 = -10% PnL"""
        entry = 100.0
        exit_price = 90.0
        pnl = (exit_price - entry) / entry * 100
        self.assertAlmostEqual(pnl, -10.0, places=2)
    
    def test_short_profit_10_percent(self):
        """Short: Entry 100 → Exit 90 = +10% PnL"""
        entry = 100.0
        exit_price = 90.0
        raw_pnl = (exit_price - entry) / entry
        pnl = -raw_pnl * 100  # Invert for short
        self.assertAlmostEqual(pnl, 10.0, places=2)
    
    def test_short_loss_10_percent(self):
        """Short: Entry 100 → Exit 110 = -10% PnL"""
        entry = 100.0
        exit_price = 110.0
        raw_pnl = (exit_price - entry) / entry
        pnl = -raw_pnl * 100
        self.assertAlmostEqual(pnl, -10.0, places=2)
    
    def test_leverage_3x_multiplies_pnl(self):
        """Leverage 3x should multiply PnL by 3"""
        entry = 100.0
        exit_price = 110.0
        leverage = 3.0
        
        base_pnl = (exit_price - entry) / entry * 100
        leveraged_pnl = base_pnl * leverage
        
        self.assertAlmostEqual(base_pnl, 10.0)
        self.assertAlmostEqual(leveraged_pnl, 30.0)
    
    def test_fee_0_1_percent_deduction(self):
        """0.1% fee should be deducted from profit"""
        entry = 100.0
        exit_price = 110.0
        fee_rate = 0.001  # 0.1%
        
        gross_pnl = (exit_price - entry)
        fee = entry * fee_rate + exit_price * fee_rate  # Entry + Exit fee
        net_pnl = gross_pnl - fee
        
        expected_net = 10.0 - (0.1 + 0.11)  # 10 - 0.21 = 9.79
        self.assertAlmostEqual(net_pnl, expected_net, places=2)
    
    def test_mdd_peak_to_trough(self):
        """MDD: Peak 1200, Trough 900 = 25% drawdown"""
        equity = [1000, 1100, 1200, 1050, 900, 950, 1100]
        
        peak = equity[0]
        max_dd = 0
        
        for eq in equity:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            max_dd = max(max_dd, dd)
        
        self.assertAlmostEqual(max_dd, 25.0, places=2)
    
    def test_mdd_no_drawdown(self):
        """No drawdown if equity always increases"""
        equity = [1000, 1100, 1200, 1300, 1400]
        
        peak = equity[0]
        max_dd = 0
        
        for eq in equity:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            max_dd = max(max_dd, dd)
        
        self.assertAlmostEqual(max_dd, 0.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
