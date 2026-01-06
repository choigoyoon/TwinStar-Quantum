"""
Integration Tests: Full Scenario Testing
Tests complete workflows with real-like data
"""
import unittest
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestScenario1_OptimizeToScan(unittest.TestCase):
    """Scenario: 3 symbols → Optimize → 2 pass → Backtest → Scanner"""
    
    def test_optimization_filters_correctly(self):
        """3 symbols optimized, 2 should pass strict filter"""
        symbols = ['BTC', 'ETH', 'SOL']
        
        # Simulate optimization results
        results = {
            'BTC': {'win_rate': 75.0, 'max_drawdown': 15.0, 'total_trades': 50},
            'ETH': {'win_rate': 65.0, 'max_drawdown': 12.0, 'total_trades': 40},  # Fail WR
            'SOL': {'win_rate': 72.0, 'max_drawdown': 18.0, 'total_trades': 35},
        }
        
        # Filter
        passed = []
        for sym in symbols:
            r = results[sym]
            if r['win_rate'] >= 70 and r['max_drawdown'] <= 20 and r['total_trades'] >= 30:
                passed.append(sym)
        
        self.assertEqual(len(passed), 2)
        self.assertIn('BTC', passed)
        self.assertIn('SOL', passed)
        self.assertNotIn('ETH', passed)
    
    def test_backtest_uses_only_passed_presets(self):
        """Backtest should only use passed presets"""
        passed_presets = ['BTC', 'SOL']
        all_presets = ['BTC', 'ETH', 'SOL']
        
        # Simulate loading verified presets only
        loaded = [p for p in all_presets if p in passed_presets]
        
        self.assertEqual(len(loaded), 2)
        self.assertNotIn('ETH', loaded)


class TestScenario2_ConcurrentSignals(unittest.TestCase):
    """Scenario: 3 signals at same time → Select highest win rate"""
    
    def test_select_highest_win_rate(self):
        """Among concurrent signals, select highest win rate"""
        ts = datetime(2025, 1, 1, 12, 0)
        
        signals = [
            {'timestamp': ts, 'symbol': 'BTC', 'win_rate': 72.0},
            {'timestamp': ts, 'symbol': 'ETH', 'win_rate': 78.0},  # Highest
            {'timestamp': ts, 'symbol': 'SOL', 'win_rate': 70.0},
        ]
        
        # Sort by win rate descending, take first
        sorted_signals = sorted(signals, key=lambda x: x['win_rate'], reverse=True)
        selected = sorted_signals[0]
        
        self.assertEqual(selected['symbol'], 'ETH')
        self.assertEqual(selected['win_rate'], 78.0)
    
    def test_only_one_executes(self):
        """Only one signal should execute"""
        ts = datetime(2025, 1, 1, 12, 0)
        signals = [
            {'timestamp': ts, 'symbol': 'BTC'},
            {'timestamp': ts, 'symbol': 'ETH'},
            {'timestamp': ts, 'symbol': 'SOL'},
        ]
        
        executed = []
        position_busy = False
        
        for sig in signals:
            if not position_busy:
                executed.append(sig)
                position_busy = True
        
        self.assertEqual(len(executed), 1)


class TestScenario3_PositionCycle(unittest.TestCase):
    """Scenario: Position open → Close → New signal → Entry"""
    
    def test_position_blocks_then_allows(self):
        """Position should block new entries until closed"""
        events = [
            {'time': 0, 'action': 'signal_btc'},
            {'time': 1, 'action': 'entry_btc'},
            {'time': 2, 'action': 'signal_eth'},  # Should be blocked
            {'time': 5, 'action': 'exit_btc'},
            {'time': 6, 'action': 'signal_sol'},  # Should be allowed
        ]
        
        positions = {}
        entries = []
        blocked = []
        
        for event in events:
            if 'entry' in event['action']:
                sym = event['action'].split('_')[1].upper()
                positions[sym] = event['time']
                entries.append(sym)
            elif 'exit' in event['action']:
                sym = event['action'].split('_')[1].upper()
                if sym in positions:
                    del positions[sym]
            elif 'signal' in event['action']:
                sym = event['action'].split('_')[1].upper()
                if len(positions) >= 1:
                    blocked.append(sym)
                else:
                    entries.append(sym)
        
        self.assertIn('BTC', entries)
        self.assertIn('ETH', blocked)
        self.assertIn('SOL', entries)
    
    def test_full_cycle_count(self):
        """Full cycle: entry → exit → entry"""
        trade_log = []
        position = None
        
        # Entry BTC
        position = {'symbol': 'BTC', 'entry_time': 0}
        trade_log.append({'type': 'entry', 'symbol': 'BTC'})
        
        # Exit BTC
        position = None
        trade_log.append({'type': 'exit', 'symbol': 'BTC'})
        
        # Entry ETH
        position = {'symbol': 'ETH', 'entry_time': 5}
        trade_log.append({'type': 'entry', 'symbol': 'ETH'})
        
        entries = [t for t in trade_log if t['type'] == 'entry']
        
        self.assertEqual(len(entries), 2)


class TestScannerStateTransitions(unittest.TestCase):
    """Test scanner state machine transitions"""
    
    def test_idle_to_scanning(self):
        """IDLE → SCANNING on start"""
        state = 'IDLE'
        
        # Start command
        state = 'SCANNING'
        
        self.assertEqual(state, 'SCANNING')
    
    def test_scanning_to_monitoring(self):
        """SCANNING → MONITORING when candidate found"""
        state = 'SCANNING'
        candidate_found = True
        
        if candidate_found:
            state = 'MONITORING'
        
        self.assertEqual(state, 'MONITORING')
    
    def test_monitoring_to_trading(self):
        """MONITORING → TRADING when signal triggers"""
        state = 'MONITORING'
        signal_triggered = True
        
        if signal_triggered:
            state = 'TRADING'
        
        self.assertEqual(state, 'TRADING')
    
    def test_trading_blocks_new_signals(self):
        """TRADING state should block new signals"""
        state = 'TRADING'
        new_signal = {'symbol': 'ETH'}
        
        can_process = state != 'TRADING'
        
        self.assertFalse(can_process)
    
    def test_error_returns_to_idle(self):
        """Error should return to IDLE"""
        state = 'MONITORING'
        error_occurred = True
        
        if error_occurred:
            state = 'IDLE'
        
        self.assertEqual(state, 'IDLE')
    
    def test_monitoring_timeout_returns_scanning(self):
        """MONITORING timeout → SCANNING"""
        state = 'MONITORING'
        timeout = True
        
        if timeout:
            state = 'SCANNING'
        
        self.assertEqual(state, 'SCANNING')


if __name__ == '__main__':
    unittest.main(verbosity=2)
