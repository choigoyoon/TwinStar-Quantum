#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_critical_gui.py - Verification for Critical Modules (Part C)
Target: GUI/trading_dashboard.py (Logic Only)
"""
import unittest
import logging
import json
import os
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path
import sys

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Mock PyQt5 before importing GUI
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtWidgets'] = MagicMock()
sys.modules['PyQt5.QtCore'] = MagicMock()
sys.modules['PyQt5.QtGui'] = MagicMock()

# Mock components that might be imported
sys.modules['GUI.dashboard_widgets'] = MagicMock()
sys.modules['GUI.position_widget'] = MagicMock()
sys.modules['GUI.components.workers'] = MagicMock()
sys.modules['GUI.components.bot_control_card'] = MagicMock()
sys.modules['GUI.dashboard.multi_explorer'] = MagicMock()
sys.modules['GUI.components.market_status'] = MagicMock()

# Import target
from GUI.trading_dashboard import TradingDashboard

logging.basicConfig(level=logging.INFO)

class TestCriticalGUI(unittest.TestCase):
    
    def setUp(self):
        # Ensure license_manager is mocked in sys.modules
        if 'license_manager' not in sys.modules:
            sys.modules['license_manager'] = MagicMock()
            
    def test_01_max_coins_limit(self):
        """[Dashboard] _get_max_coins respects tier"""
        # Create instance without init
        dashboard = TradingDashboard.__new__(TradingDashboard)
        
        # Helper to check limit based on tier return
        def check_limit(tier, expected):
            # Mock the module that _get_max_coins imports
            mock_lm_module = sys.modules['license_manager']
            mock_lm_instance = mock_lm_module.get_license_manager.return_value
            mock_lm_instance.get_tier.return_value = tier
            
            limit = dashboard._get_max_coins()
            self.assertEqual(limit, expected, f"Failed for tier {tier}")

        check_limit('PREMIUM', 9999)
        check_limit('ADMIN', 9999)
        check_limit('STANDARD', 3)
        check_limit('BASIC', 1)
        
        print("✅ [Dashboard] Tier limit logic verified")

    def test_02_save_state(self):
        """[Dashboard] save_state logic"""
        dashboard = TradingDashboard.__new__(TradingDashboard)
        
        # Manually set attributes used by save_state
        dashboard.is_loading = False
        
        # Setup Dummy Rows
        row1 = MagicMock()
        row1.exchange_combo.currentText.return_value = 'bybit'
        row1.symbol_combo.currentText.return_value = 'BTCUSDT'
        row1.preset_combo.currentText.return_value = 'Default'
        row1.leverage_spin.value.return_value = 10
        row1.seed_spin.value.return_value = 100
        row1.start_btn.text.return_value = "Run" # Active if "Stop"
        
        dashboard.coin_rows = [row1]
        
        # Mock json dump
        with patch('json.dump') as mock_json_dump, \
             patch('builtins.open', new_callable=MagicMock), \
             patch('pathlib.Path.mkdir'):
            
            dashboard.save_state()
            
            # Verify data structure
            args, _ = mock_json_dump.call_args
            data = args[0]
            
            self.assertIn('rows', data)
            self.assertEqual(len(data['rows']), 1)
            self.assertEqual(data['rows'][0]['symbol'], 'BTCUSDT')
            
        print("✅ [Dashboard] State save logic verified")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
