#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_phase3_batch1.py - GUI Phase 3 Batch 1 Tests
Widgets:
1. PositionStatusWidget (GUI/position_widget.py)
2. NotificationWidget (GUI/notification_widget.py)
3. NowcastWidget (GUI/nowcast_widget.py)
4. MultiSystemWidget (GUI/multi_system_widget.py) - Includes MultiBacktest logic
"""
import sys
import os
from pathlib import Path
import logging
import unittest
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
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

def run_batch1_tests():
    print("\n" + "="*60)
    print("🧪 Phase 3 Batch 1 Tests")
    print("="*60)
    
    result = TestResult()
    
    # ---------------------------------------------------------
    # 1. PositionWidget (PositionStatusWidget)
    # ---------------------------------------------------------
    print("\n[1. PositionStatusWidget]")
    try:
        from GUI.position_widget import PositionStatusWidget
        print("  ✅ Import Successful")
        
        widget = PositionStatusWidget()
        result.ok("Instance Created", widget is not None)
        
        # Test Methods
        result.ok("add_position exists", hasattr(widget, 'add_position'))
        result.ok("remove_position exists", hasattr(widget, 'remove_position'))
        result.ok("update_position exists", hasattr(widget, 'update_position'))
        
        # Add a position
        try:
            widget.add_position("BTCUSDT", "LONG", 50000, 51000, 49000, 0.1)
            result.ok("add_position executed", "BTCUSDT" in widget.positions)
            
            widget.update_position("BTCUSDT", 52000)
            # Check price update logic implicitly (no crash)
            result.ok("update_position executed", True)
            
            widget.remove_position("BTCUSDT")
            result.ok("remove_position executed", "BTCUSDT" not in widget.positions)
            
        except Exception as e:
            result.ok("Functional Test Failed", False, str(e))
            
        widget.close()
        
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    # ---------------------------------------------------------
    # 2. NotificationWidget
    # ---------------------------------------------------------
    print("\n[2. NotificationWidget]")
    try:
        # Mock NotificationManager globally (Source)
        with patch('notification_manager.NotificationManager') as MockNM:
            # Force reload to ensure patch is picked up during import
            if 'GUI.notification_widget' in sys.modules:
                del sys.modules['GUI.notification_widget']
                
            # Configure Mock to return settings object with string attributes
            instance = MockNM.return_value
            
            # Create a mock settings object with necessary attributes
            mock_settings = MagicMock()
            mock_settings.telegram_token = "dummy_token"
            mock_settings.telegram_chat_id = "dummy_chat_id"
            mock_settings.discord_webhook = "dummy_webhook"
            mock_settings.telegram_enabled = False
            mock_settings.discord_enabled = False
            mock_settings.sound_enabled = True
            mock_settings.daily_report_time = "09:00"
            
            # Key fix: NotificationWidget accesses .settings attribute, not get_settings()
            instance.settings = mock_settings
            instance.get_settings.return_value = mock_settings
            
            import GUI.notification_widget
            widget = GUI.notification_widget.NotificationWidget()
            print("  ✅ Import Successful")
            result.ok("Instance Created", widget is not None)
            
            # Test UI components
            result.ok("Telegram Section exists", hasattr(widget, 'chk_telegram') and hasattr(widget, 'txt_telegram_token'))
            result.ok("Discord Section exists", hasattr(widget, 'chk_discord') and hasattr(widget, 'txt_discord_webhook'))
            
            # Test Methods
            result.ok("_load_current_settings exists", hasattr(widget, '_load_current_settings'))
            result.ok("_on_save exists", hasattr(widget, '_on_save'))
            
            widget.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    # ---------------------------------------------------------
    # 3. NowcastWidget
    # ---------------------------------------------------------
    print("\n[3. NowcastWidget]")
    try:
        from GUI.nowcast_widget import NowcastWidget
        print("  ✅ Import Successful")
        
        widget = NowcastWidget()
        result.ok("Instance Created", widget is not None)
        
        # Test Methods
        result.ok("get_base_timeframe exists", hasattr(widget, 'get_base_timeframe'))
        result.ok("get_selected_timeframes exists", hasattr(widget, 'get_selected_timeframes'))
        
        # Functional Test
        tf = widget.get_base_timeframe()
        result.ok("get_base_timeframe returns string", isinstance(tf, str))
        
        widget.close()
        
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    # ---------------------------------------------------------
    # 4. MultiSystemWidget (Includes MultiBacktest)
    # ---------------------------------------------------------
    print("\n[4. MultiSystemWidget]")
    try:
        # Mock Core dependencies
        with patch('GUI.multi_system_widget.MultiOptimizer'), \
             patch('GUI.multi_system_widget.MultiBacktester'), \
             patch('GUI.multi_system_widget.DualTrackTrader'):
             
            from GUI.multi_system_widget import MultiSystemWidget
            print("  ✅ Import Successful")
            
            widget = MultiSystemWidget()
            result.ok("Instance Created", widget is not None)
            
            # Check Tabs (Optimizer, Backtest, Trader)
            # Assuming QTabWidget is used
            if hasattr(widget, 'tabs'):
                count = widget.tabs.count()
                result.ok("Tabs Created", count >= 2) # At least Optimizer and Backtest
            else:
                # Might inherit from QTabWidget directly?
                # Checked code: inherits QWidget, has self.tabs = QTabWidget()
                result.ok("Tabs attribute exists", hasattr(widget, 'tab_widget') or hasattr(widget, 'tabs'))

            # Check Methods
            result.ok("_run_multi_optimization exists", hasattr(widget, '_run_multi_optimization'))
            result.ok("_run_multi_backtest exists", hasattr(widget, '_run_multi_backtest'))
            
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
    result = run_batch1_tests()
    sys.exit(0 if result.failed == 0 else 1)
