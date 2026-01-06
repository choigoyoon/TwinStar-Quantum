"""
Verify Scanner Real Logic
- Mocks External API (ExchangeManager, AlphaX7Core)
- Tests Integration Flow: Verified Symbols -> config -> Data Fetch -> Signal -> Execution (Dry Run)
"""
import sys
import os
import unittest
import logging
from unittest.mock import MagicMock, patch
from PyQt5.QtCore import QCoreApplication
from datetime import datetime

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.auto_scanner import AutoScanner

class TestScannerRealLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QCoreApplication.instance():
            cls.app = QCoreApplication([])

    def setUp(self):
        # Config for Dry Run
        self.config = {
            'entry_amount': 100,
            'leverage': 5, 
            'max_positions': 2,
            'priority': 'win_rate',
            'interval': 0.1,
            'dry_run': True # Critical for test
        }
        
    @patch('core.auto_scanner.get_exchange_manager')
    @patch('core.auto_scanner.get_preset_manager')
    def test_real_scan_flow(self, mock_pm_func, mock_em_func):
        print("\n=== [Real Logic] Verifying Scanner Integration ===")
        
        # 1. Setup Mock PresetManager
        scaler = AutoScanner(self.config)
        
        mock_pm = mock_pm_func.return_value
        mock_pm.list_presets.return_value = ['bybit_BTCUSDT_1h', 'bybit_ETHUSDT_1h']
        
        # Mock verification status + params
        def get_status(name):
             return {'passed': True, 'win_rate': 80 if 'BTC' in name else 90}
        mock_pm.get_verification_status.side_effect = get_status
        
        def load_preset(name):
             return {'params': {'rsi_period': 14}}
        mock_pm.load_preset.side_effect = load_preset
        
        # Load Symbols
        scaler.load_verified_symbols()
        self.assertEqual(len(scaler.verified_symbols), 2)
        print("✅ Verified Symbols Loaded")
        
        # 2. Setup Mock ExchangeManager
        mock_em = mock_em_func.return_value
        mock_exchange = MagicMock()
        mock_em.get_exchange.return_value = mock_exchange
        
        # Mock Data Fetch (return dummy df)
        mock_exchange.get_klines.return_value = "dummy_df" # Strategy mock will handle this
        mock_exchange.get_current_price.return_value = 50000.0
        
        # 3. Setup Strategy Integration
        # We Mock the strategy instance inside scanner
        scaler.strategy = MagicMock()
        
        # Make BTC return NO signal, ETH return Signal
        # Mock return: [SignalObj]
        sig_eth = MagicMock()
        sig_eth.signal_type = 'buy'
        sig_eth.timestamp = datetime.now() # fresh
        sig_eth.stop_loss = 49000
        
        def detect_signal(df1, df2, **kwargs):
             # We can distinguish by some way, but easiest is to return signals for both and let Priority sort.
             # Or use side_effect to return different values on sequential calls.
             return [sig_eth]
        
        scaler.strategy.detect_signal.return_value = [sig_eth]
        
        # 4. Run Scan (Mocked)
        scaler.running = True
        
        # Connect signal to verify execution
        executed = []
        scaler.position_opened.connect(lambda x: executed.append(x))
        
        # Run Once
        with patch('time.sleep', return_value=None):
             scaler._scan_once()
             
        # 5. Verify Execution
        # Since logic sorts by WR, ETH (90) > BTC (80). Strategy returns signal for both (as configured above).
        # We expect ETH execution first.
        
        self.assertTrue(len(executed) > 0, "No trade executed")
        trade = executed[0]
        self.assertEqual(trade['symbol'], 'ETHUSDT') # Higher WR
        self.assertTrue(trade.get('dry_run'), "Dry Run flag missing")
        print(f"✅ Trade Executed (Dry Run): {trade['symbol']} @ {trade.get('price')}")
        
        # Verify Exchange Calls
        mock_exchange.get_klines.assert_called()
        mock_exchange.get_current_price.assert_called()
        # Verify Place Order NOT called (because of dry run check inside _execute_entry? 
        # Wait, inside _execute_entry in real code:
        # if dry_run: emit signal, return.
        # So place_market_order should NOT be called.
        mock_exchange.place_market_order.assert_not_called()
        print("✅ Real Order Skipped (Safe)")
        
        # Verify set_leverage called
        if hasattr(mock_exchange, 'set_leverage'):
             mock_exchange.set_leverage.assert_called()

if __name__ == '__main__':
    unittest.main()
