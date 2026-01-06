import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.auto_scanner import AutoScanner

from PyQt5.QtCore import QCoreApplication

class TestAutoScanner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        self.config = {
            'entry_amount': 100,
            'max_positions': 2,
            'priority': 'win_rate',
            'interval': 0.1
        }
        self.scanner = AutoScanner(self.config)
        
    @patch('utils.preset_manager.get_preset_manager')
    def test_load_verified(self, mock_pm_func):
        mock_pm = mock_pm_func.return_value
        mock_pm.list_presets.return_value = ['bybit_BTCUSDT_1h', 'bybit_ETHUSDT_1h']
        mock_pm.get_verification_status.side_effect = [
            {'passed': True, 'win_rate': 80},
            {'passed': False}
        ]
        
        self.scanner.preset_manager = mock_pm
        self.scanner.load_verified_symbols()
        
        self.assertEqual(len(self.scanner.verified_symbols), 1)
        self.assertEqual(self.scanner.verified_symbols[0]['symbol'], 'BTCUSDT')

    def test_scan_logic(self):
        # Setup verified symbols
        self.scanner.verified_symbols = [
            {'symbol': 'BTCUSDT', 'stats': {'win_rate': 80}},
            {'symbol': 'ETHUSDT', 'stats': {'win_rate': 90}}
        ]
        
        # Connect signal
        emitted_signals = []
        self.scanner.position_opened.connect(lambda x: emitted_signals.append(x))
        
        # Enable scanner
        self.scanner.running = True
        
        # Run scan once
        # Mocking logic where ETH has higher WR, so passed priority
        # Sequence: BTC Hit(T), BTC Dir, ETH Hit(T), ETH Dir
        with patch('random.random', side_effect=[0.01, 0.01, 0.01, 0.01]): 
            self.scanner._scan_once()
            
        # Should execute ETH because 90 > 80
        self.assertTrue(len(emitted_signals) > 0)
        entry = emitted_signals[0]
        self.assertEqual(entry['symbol'], 'ETHUSDT')

if __name__ == '__main__':
    unittest.main()
