"""
Verify Full Pipeline (Step 4)
- Tests: End-to-End UI Flow from Symbol Selection to Scanner Start
"""
import sys
import os
import unittest
from typing import Any
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication, QMessageBox, QWidget

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from GUI.auto_pipeline_widget import AutoPipelineWidget

class TestFullPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.widget = AutoPipelineWidget()
        
    @patch('PyQt5.QtWidgets.QMessageBox.information')
    @patch('PyQt5.QtWidgets.QMessageBox.warning')
    def test_e2e_flow(self, mock_warning, mock_info):
        print("\n\n=== [Step 4] Verifying Full Pipeline Flow ===")
        
        # --- Step 1: Symbol Selection ---
        print("▶️ [Step 1] Loading Symbols...")
        self.widget._load_symbols() # Mock load
        
        # Select first 3 symbols (Uncheck all first)
        from PyQt6.QtCore import Qt
        
        for i in range(self.widget.symbol_list.count()):
            item = self.widget.symbol_list.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Unchecked) # Uncheck

        for i in range(3):
            item = self.widget.symbol_list.item(i)
            if item:
                item.setCheckState(Qt.CheckState.Checked) # Checked
        self.widget._update_selection_count()
        print(f"  Selected: {len(self.widget.selected_symbols)}")
        self.assertEqual(len(self.widget.selected_symbols), 3)
        
        self.widget._go_next()
        self.assertEqual(self.widget.stack.currentIndex(), 1)
        
        # --- Step 2: Batch Optimization ---
        print("▶️ [Step 2] Optimizing...")
        self.widget.mode_combo.setCurrentIndex(0) # Quick
        self.widget._start_optimization()
        
        # Simulate progress completion
        if hasattr(self.widget, '_prog'):
            setattr(self.widget, '_prog', 99)
        if hasattr(self.widget, '_simulate_progress'):
            getattr(self.widget, '_simulate_progress')()
        print("  Optimization simulated complete")
        
        self.assertEqual(self.widget.stack.currentIndex(), 2)
        
        # --- Step 3: Verification ---
        print("▶️ [Step 3] Verifying...")
        
        # Mocking BatchVerifier to return pass for our selected symbols
        with patch('core.batch_verifier.BatchVerifier') as MockVerifier:
            verifier = MockVerifier.return_value
            # Return pass for ALL selected
            verifier.verify_presets.return_value = [
                {'symbol': sym, 'win_rate': 80, 'mdd': 10, 'passed': True} 
                for sym in self.widget.selected_symbols
            ]
            
            if hasattr(self.widget, '_run_verification'):
                getattr(self.widget, '_run_verification')()
            
            verified_len = len(getattr(self.widget, 'verified_symbols', []))
            print(f"  Verified: {verified_len}")
            self.assertEqual(verified_len, 3)
            
            self.widget._go_next()
            self.assertEqual(self.widget.stack.currentIndex(), 3)
            
        # --- Step 4: Scanner Config ---
        print("▶️ [Step 4] Starting Scanner...")
        self.widget.entry_amt.setValue(500)
        
        # Mock AutoScanner to avoid real thread start issues in test
        with patch('core.auto_scanner.AutoScanner') as MockScanner:
            self.widget._start_scanner()
            
            # Verify scanner init
            MockScanner.assert_called()
            if hasattr(self.widget, 'scanner') and self.widget.scanner:
                self.widget.scanner.start.assert_called()  # type: ignore[attr-defined]
            print("  Scanner started successfully")
            
            self.assertEqual(self.widget.stack.currentIndex(), 4)
            self.assertEqual(self.widget.dashboard_status.text(), "RUNNING")
            
        print("✅ Full Pipeline Flow Verified")

if __name__ == '__main__':
    unittest.main()
