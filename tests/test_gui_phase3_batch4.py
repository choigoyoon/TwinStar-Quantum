#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_gui_phase3_batch4.py - GUI Phase 3 Batch 4 Tests
Widgets:
1. MultiSessionPopup (GUI/multi_session_popup.py)
2. SniperSessionPopup (GUI/sniper_session_popup.py)
3. TradeChartDialog (GUI/trade_chart_dialog.py)
4. TradeDetailPopup (GUI/trade_detail_popup.py)
5. UpdatePopup (GUI/update_popup.py)
"""
import sys
import os
from pathlib import Path
import logging
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "GUI")) # Add GUI to path
os.chdir(PROJECT_ROOT)

logging.basicConfig(level=logging.WARNING)

from PyQt6.QtWidgets import QApplication

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
        else:
            print(f"  ❌ {name}: {msg}")
            self.failed += 1
            self.errors.append(f"{name}: {msg}")
        self.passed += 1 if condition else 0
        sys.stdout.flush()

def run_batch4_tests():
    print("\n" + "="*60)
    print("🧪 Phase 3 Batch 4 Tests (Popups & Dialogs)")
    print("="*60)
    sys.stdout.flush()
    
    result = TestResult()
    
    # ---------------------------------------------------------
    # 1. MultiSessionPopup
    # ---------------------------------------------------------
    print("\n[1. MultiSessionPopup]")
    try:
        from GUI.multi_session_popup import MultiSessionPopup
        print("  ✅ Import Successful")
        
        summary = {
            "coins": [
                {
                    "symbol": "BTC",
                    "initial_seed": 1000.0,
                    "current_seed": 1100.0,
                    "pnl_pct": 10.0,
                    "win_count": 6,
                    "trade_count": 10
                }
            ],
            "total_initial": 1000.0,
            "total_current": 1100.0,
            "total_pnl": 100.0,
            "total_pnl_pct": 10.0,
            "total_trades": 10,
            "total_wins": 6,
            "win_rate": 60.0
        }
        
        popup = MultiSessionPopup(summary)
        result.ok("Instance Created", popup is not None)
        result.ok("_on_compound exists", hasattr(popup, '_on_compound'))
        result.ok("_on_reset exists", hasattr(popup, '_on_reset'))
        
        popup.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()

    # ---------------------------------------------------------
    # 2. SniperSessionPopup
    # ---------------------------------------------------------
    print("\n[2. SniperSessionPopup]")
    try:
        from PyQt6.QtCore import Qt
        print(f"  DEBUG: Qt is {Qt}")
        print(f"  DEBUG: Qt.AlignmentFlag.AlignCenter is {Qt.AlignmentFlag.AlignCenter} type={type(Qt.AlignmentFlag.AlignCenter)}")
        
        from GUI.sniper_session_popup import SniperSessionPopup
        print("  ✅ Import Successful")
        
        summary = {
            "coins": [
                {
                    "symbol": "SOL",
                    "initial_seed": 500.0,
                    "current_seed": 520.0,
                    "pnl_pct": 4.0,
                    "win_count": 2,
                    "trade_count": 5
                }
            ],
            "total_initial": 500.0,
            "total_current": 520.0,
            "total_pnl": 20.0,
            "total_pnl_pct": 4.0,
            "total_trades": 5,
            "total_wins": 2,
            "win_rate": 40.0
        }
        
        print("  DEBUG: Instantiating SniperSessionPopup...")
        try:
            popup = SniperSessionPopup(summary)
            print("  DEBUG: Info Instantiated.")
            result.ok("Instance Created", popup is not None)
            result.ok("get_result exists", hasattr(popup, 'get_result'))
            popup.close()
        except Exception as inner_e:
            print(f"  ❌ Instantiation Error: {inner_e}")
            import traceback
            traceback.print_exc()
            raise inner_e
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()
    
    # Define StubCanvas for addWidget compatibility
    from PyQt6.QtWidgets import QWidget
    class StubCanvas(QWidget):
        def __init__(self, figure=None, parent=None):
            super().__init__(parent)
            self.figure = figure
        def draw(self): pass

    # ---------------------------------------------------------
    # 3. TradeChartDialog
    # ---------------------------------------------------------
    print("\n[3. TradeChartDialog]")
    try:
        # Mock dependencies (TradeSignal, Candle, FigureCanvas)
        with patch('strategies.common.strategy_interface.TradeSignal') as MockSignal, \
             patch('strategies.common.strategy_interface.Candle') as MockCandle, \
             patch('GUI.trade_chart_dialog.FigureCanvas', side_effect=StubCanvas):
            
            from GUI.trade_chart_dialog import TradeChartDialog
            print("  ✅ Import Successful")
            
            # Create dummy objects
            mock_trade = MagicMock()
            mock_trade.symbol = "BTC/USDT"
            mock_trade.entry_time = 1000
            mock_trade.entry_price = 50000.0
            mock_trade.exit_price = 51000.0
            mock_trade.pnl_percent = 2.0
            mock_trade.take_profit = 52000.0
            mock_trade.stop_loss = 49000.0
            mock_trade.candle_index = 0
            
            # Helper for signal status
            mock_trade.signal_type = MagicMock()
            mock_trade.signal_type.value = "long"
            
            mock_candle = MagicMock()
            mock_candle.timestamp = 1000
            mock_candle.open = 100.0
            mock_candle.high = 110.0
            mock_candle.low = 90.0
            mock_candle.close = 105.0
            
            # Use real QDialog but mock layout/charting if complex
            with patch.object(TradeChartDialog, '_plot_chart'):
                dialog = TradeChartDialog(mock_trade, [mock_candle])
                result.ok("Instance Created", dialog is not None)
                result.ok("_save_image exists", hasattr(dialog, '_save_image'))
                
                dialog.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()
    
    # ---------------------------------------------------------
    # 4. TradeDetailPopup
    # ---------------------------------------------------------
    print("\n[4. TradeDetailPopup]")
    try:
        from GUI.trade_detail_popup import TradeDetailPopup
        print("  ✅ Import Successful")
        
        # Prepare dummy data
        trades = [{
            'symbol': 'BTC/USDT',
            'entry_time': '2024-01-01 12:00:00',
            'exit_time': '2024-01-01 14:00:00',
            'entry_price': 50000.0,
            'exit_price': 51000.0,
            'initial_sl': 49000.0, 
            'pnl': 100.0,
            'entry_idx': 0, 
            'exit_idx': 1
        }]
        
        df = pd.DataFrame({
            'timestamp': [1000, 2000],
            'open': [50000.0, 50500.0],
            'high': [51000.0, 51500.0],
            'low': [49000.0, 49500.0],
            'close': [50500.0, 51000.0]
        })
        
        # Patch matplotlib canvas
        with patch('GUI.trade_detail_popup.FigureCanvas', side_effect=StubCanvas), \
             patch('GUI.trade_detail_popup.Figure'), \
             patch.object(TradeDetailPopup, '_draw_chart'): # Skip actual drawing logic
             
            popup = TradeDetailPopup(trades, df)
            result.ok("Instance Created", popup is not None)
            result.ok("go_to_trade exists", hasattr(popup, 'go_to_trade'))
            result.ok("_update_display exists", hasattr(popup, '_update_display'))
            
            popup.close()
            
    except Exception as e:
        result.ok("Import/Init Failed", False, str(e))

    sys.stdout.flush()
    
    # ---------------------------------------------------------
    # 5. UpdatePopup
    # ---------------------------------------------------------
    print("\n[5. UpdatePopup]")
    try:
        # Mock core.updater
        mock_updater_mod = MagicMock()
        mock_updater = MagicMock()
        mock_updater.current_version = "1.0.0"
        mock_updater_mod.get_updater.return_value = mock_updater
        
        with patch.dict(sys.modules, {'core.updater': mock_updater_mod}), \
             patch('GUI.update_popup.DownloadWorker'): # Mock worker
            
            from GUI.update_popup import UpdatePopup
            print("  ✅ Import Successful")
            
            popup = UpdatePopup()
            result.ok("Instance Created", popup is not None)
            result.ok("_on_check exists", hasattr(popup, '_on_check'))
            result.ok("_on_update exists", hasattr(popup, '_on_update'))
            
            popup.close()
            
    except Exception as e:
        import traceback
        traceback.print_exc()
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
    result = run_batch4_tests()
    sys.exit(0 if result.failed == 0 else 1)
