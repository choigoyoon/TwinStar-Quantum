#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_phase3_batch2.py - GUI Phase 3 Batch 2 Tests
Widgets:
1. CacheManagerWidget (GUI/cache_manager_widget.py)
2. CapitalManagementWidget (GUI/capital_management_widget.py)
3. DataDownloadWidget (GUI/data_download_widget.py)
4. EquityCurveWidget (GUI/dashboard_widgets.py)
5. ExchangeSelectorWidget (GUI/exchange_selector_widget.py)
"""
import sys
import os
from pathlib import Path
import logging
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "GUI")) # Add GUI to path for internal imports
os.chdir(PROJECT_ROOT)

logging.basicConfig(level=logging.WARNING)

from PyQt5.QtWidgets import QApplication

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

def run_batch2_tests():
    print("\n" + "="*60)
    print("🧪 Phase 3 Batch 2 Tests")
    print("="*60)
    
    result = TestResult()
    
    # ---------------------------------------------------------
    # 1. CacheManagerWidget
    # ---------------------------------------------------------
    print("\n[1. CacheManagerWidget]")
    try:
        # Mock DataManager
        with patch('GUI.cache_manager_widget.DataManager') as MockDM:
            # Configure mock return for get_all_cache_list
            MockDM.return_value.get_all_cache_list.return_value = [
                {'exchange': 'Binance', 'symbol': 'BTC/USDT', 'timeframe': '1h', 
                 'first_date': '2023-01-01', 'last_date': '2023-01-31', 
                 'count': 1000, 'file_size': 1.5, 'filename': 'test.parquet'}
            ]
            
            from GUI.cache_manager_widget import CacheManagerWidget
            print("  ✅ Import Successful")
            
            widget = CacheManagerWidget()
            result.ok("Instance Created", widget is not None)
            result.ok("load_cache_list exists", hasattr(widget, 'load_cache_list'))
            result.ok("delete_cache exists", hasattr(widget, 'delete_cache'))
            result.ok("delete_all_caches exists", hasattr(widget, 'delete_all_caches'))
            
            # Test table population
            widget.load_cache_list()
            result.ok("Table populated", widget.table.rowCount() == 1)
            
            widget.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    # ---------------------------------------------------------
    # 2. CapitalManagementWidget
    # ---------------------------------------------------------
    print("\n[2. CapitalManagementWidget]")
    try:
        # Mock capital_config
        with patch('GUI.capital_management_widget.get_position_sizer') as MockSizer:
            mock_sizer = MagicMock()
            mock_sizer.config = MagicMock()
            # Set explicit values for QSpinBox/QDoubleSpinBox
            mock_sizer.config.risk_per_trade = 1.0
            mock_sizer.config.max_position_size = 1000.0
            mock_sizer.config.stop_loss_pct = 2.0
            mock_sizer.config.leverage = 5
            mock_sizer.config.entry_percent = 50.0
            
            MockSizer.return_value = mock_sizer
            
            from GUI.capital_management_widget import CapitalManagementWidget
            print("  ✅ Import Successful")
            
            widget = CapitalManagementWidget()
            result.ok("Instance Created", widget is not None)
            result.ok("update_config exists", hasattr(widget, 'update_config'))
            result.ok("calculate_position exists", hasattr(widget, 'calculate_position'))
            
            widget.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    # ---------------------------------------------------------
    # 3. DataDownloadWidget
    # ---------------------------------------------------------
    print("\n[3. DataDownloadWidget]")
    try:
        # Define a Stub that inherits QWidget to satisfy addWidget()
        from PyQt5.QtWidgets import QWidget
        from PyQt5.QtCore import pyqtSignal
        
        class StubExchangeSelector(QWidget):
            symbol_changed = pyqtSignal(str, str, str)
            def __init__(self, *args, **kwargs):
                super().__init__()
                
        # Mock dependencies (ExchangeSelectorWidget, DataManager)
        with patch('GUI.data_download_widget.ExchangeSelectorWidget', side_effect=StubExchangeSelector), \
             patch('GUI.data_download_widget.DataManager'):
            
            from GUI.data_download_widget import DataDownloadWidget
            print("  ✅ Import Successful")
            
            widget = DataDownloadWidget()
            result.ok("Instance Created", widget is not None)
            result.ok("start_download exists", hasattr(widget, 'start_download'))
            result.ok("stop_download exists", hasattr(widget, 'stop_download'))
            result.ok("find_listing_date exists", hasattr(widget, 'find_listing_date'))
            
            widget.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    # ---------------------------------------------------------
    # 4. EqualityCurveWidget (from dashboard_widgets.py)
    # ---------------------------------------------------------
    print("\n[4. EquityCurveWidget]")
    try:
        # It's in dashboard_widgets.py
        from GUI.dashboard_widgets import EquityCurveWidget
        print("  ✅ Import Successful")
        
        widget = EquityCurveWidget()
        result.ok("Instance Created", widget is not None)
        result.ok("update_data exists", hasattr(widget, 'update_data'))
        
        # Test updating with dummy data
        dummy_trades = [
            {'exit_time': '2024-01-01', 'pnl': 100},
            {'exit_time': '2024-01-02', 'pnl': -50},
            {'exit_time': '2024-01-03', 'pnl': 200},
        ]
        try:
            widget.update_data(dummy_trades)
            result.ok("update_data executed", True)
        except Exception as e:
            result.ok("update_data Failed", False, str(e))
            
        widget.close()
        
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    # ---------------------------------------------------------
    # 5. ExchangeSelectorWidget
    # ---------------------------------------------------------
    print("\n[5. ExchangeSelectorWidget]")
    try:
        # Mock ExchangeManager
        with patch('GUI.exchange_selector_widget.ExchangeManager') as MockEM:
            mock_em = MockEM.return_value
            mock_em.get_all_exchanges.return_value = ['Binance', 'Bybit']
            mock_em.get_market_types.return_value = ['spot', 'future']
            mock_em.get_symbols.return_value = [{'symbol': 'BTC/USDT'}, {'symbol': 'ETH/USDT'}] # Fix: List of dicts
            mock_em.get_ticker.return_value = {'price': 50000, 'change_24h': 1.5}
            
            from GUI.exchange_selector_widget import ExchangeSelectorWidget
            print("  ✅ Import Successful")
            
            widget = ExchangeSelectorWidget()
            result.ok("Instance Created", widget is not None)
            result.ok("load_exchanges exists", hasattr(widget, 'load_exchanges'))
            result.ok("load_symbols exists", hasattr(widget, 'load_symbols'))
            result.ok("update_ticker exists", hasattr(widget, 'update_ticker'))
            
            # Test selection change logic (manually triggering methods)
            widget.on_exchange_changed(0)
            result.ok("on_exchange_changed executed", True)
            
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
    result = run_batch2_tests()
    sys.exit(0 if result.failed == 0 else 1)
