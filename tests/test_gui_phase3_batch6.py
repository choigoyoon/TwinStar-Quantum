#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_phase3_batch6.py - GUI Phase 3 Batch 6 Tests (Final Cleanup)
Widgets:
1. BotStatusWidget (GUI/bot_status_widget.py)
2. ExchangeSelectorWidget (GUI/exchange_selector_widget.py)
3. TelegramPopup (GUI/telegram_popup.py)
4. CacheManagerWidget (GUI/cache_manager_widget.py)
"""
import sys
import os
from pathlib import Path
import logging
import unittest
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QWidget, QDialog
from PyQt6.QtCore import Qt, QTimer

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "GUI"))
os.chdir(PROJECT_ROOT)

logging.basicConfig(level=logging.WARNING)

# Initialize QApplication once
app = QApplication.instance() or QApplication(sys.argv)

class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def ok(self, name, condition, msg=""):
        if condition:
            print(f"  ✅ {name}")
            self.passed += 1
        else:
            print(f"  ❌ {name}: {msg}")
            self.failed += 1
            self.errors.append(f"{name}: {msg}")
        sys.stdout.flush()

def run_batch6_tests():
    print("\n" + "="*60)
    print("🧪 Phase 3 Batch 6 Tests (Cleanup)")
    print("="*60)
    sys.stdout.flush()
    
    result = TestResult()
    
    # ---------------------------------------------------------
    # 1. BotStatusWidget
    # ---------------------------------------------------------
    print("\n[1. BotStatusWidget]")
    try:
        from GUI.bot_status_widget import BotStatusWidget
        print("  ✅ Import Successful")
        
        # Mock load_bot_status to return a dummy status object
        mock_status = MagicMock()
        mock_status.running = True
        mock_status.exchange = "Binance"
        mock_status.symbol = "BTC/USDT"
        mock_status.position_side = "Long"
        mock_status.entry_price = 50000.0
        mock_status.current_price = 51000.0
        mock_status.stop_loss = 49000.0
        mock_status.pnl_percent = 2.0
        mock_status.pnl_usd = 100.0
        mock_status.today_trades = 5
        mock_status.today_pnl = 50.0
        
        with patch('GUI.bot_status_widget.load_bot_status', return_value=mock_status), \
             patch('GUI.bot_status_widget.get_bot_state_text', return_value=("Running", "#00FF00")):
            
            widget = BotStatusWidget()
            result.ok("Instance Created", widget is not None)
            result.ok("_refresh exists", hasattr(widget, '_refresh'))
            
            # Test refresh
            widget._refresh()
            result.ok("Refresh Logic", True)
        
            widget.close()
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()

    # ---------------------------------------------------------
    # 2. ExchangeSelectorWidget
    # ---------------------------------------------------------
    print("\n[2. ExchangeSelectorWidget]")
    try:
        from GUI.exchange_selector_widget import ExchangeSelectorWidget
        print("  ✅ Import Successful")
        
        # Mock ExchangeManager
        mock_em = MagicMock()
        mock_em.get_exchanges.return_value = ['Bybit', 'Binance']
        mock_em.get_markets.return_value = ['USDT']
        
        widget = ExchangeSelectorWidget(mock_em)
        result.ok("Instance Created", widget is not None)
        
        # Check methods
        result.ok("load_exchanges exists", hasattr(widget, 'load_exchanges'))
        result.ok("on_exchange_changed exists", hasattr(widget, 'on_exchange_changed'))
        
        widget.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()

    # ---------------------------------------------------------
    # 3. TelegramPopup
    # ---------------------------------------------------------
    print("\n[3. TelegramPopup]")
    try:
        # Mock TelegramNotifier if imported
        with patch.dict(sys.modules, {'telegram_notifier': MagicMock()}):
            from GUI.telegram_popup import TelegramPopup
            print("  ✅ Import Successful")
            
            # Init takes parent, not config dict
            popup = TelegramPopup(parent=None)
            result.ok("Instance Created", popup is not None)
            
            # Check methods
            result.ok("_save_settings exists", hasattr(popup, '_save_settings'))
            result.ok("_send_test exists", hasattr(popup, '_send_test'))
            
            popup.close()
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()
    
    # ---------------------------------------------------------
    # 4. CacheManagerWidget
    # ---------------------------------------------------------
    print("\n[4. CacheManagerWidget]")
    try:
        from GUI.cache_manager_widget import CacheManagerWidget
        print("  ✅ Import Successful")
        
        # Mock DataManager
        with patch('GUI.cache_manager_widget.DataManager') as MockDM:
            mock_instance = MockDM.return_value
            mock_instance.get_all_cache_list.return_value = [
                {'exchange': 'Bybit', 'symbol': 'BTC', 'file_size': 10.5}
            ]
            
            widget = CacheManagerWidget()
            result.ok("Instance Created", widget is not None)
            result.ok("load_cache_list exists", hasattr(widget, 'load_cache_list'))
            result.ok("delete_all_caches exists", hasattr(widget, 'delete_all_caches'))
            
            widget.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))
    
    # ===========================================
    # 결과 요약
    # ===========================================
    print("\n" + "="*60)
    total = result.passed + result.failed
    pct = result.passed / total * 100 if total > 0 else 0
    print(f"📊 결과: {result.passed}/{total} ({pct:.0f}%)")
    
    if result.failed > 0:
        print("\n실패 목록:")
        for err in result.errors:
            print(f"  - {err}")
    print("="*60)
    
    return result

if __name__ == "__main__":
    result = run_batch6_tests()
    sys.exit(0 if result.failed == 0 else 1)
