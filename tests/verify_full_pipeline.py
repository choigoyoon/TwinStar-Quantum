"""
Verify Full Pipeline (Step 4)
- Tests: End-to-End UI Flow from Symbol Selection to Scanner Start
"""
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication, QMessageBox, QWidget

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
        for i in range(self.widget.symbol_list.count()):
            self.widget.symbol_list.item(i).setCheckState(0) # Uncheck

        for i in range(3):
            item = self.widget.symbol_list.item(i)
            item.setCheckState(2) # Checked
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
        self.widget._prog = 99
        self.widget._simulate_progress()
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
            
            self.widget._run_verification()
            print(f"  Verified: {len(self.widget.verified_symbols)}")
            self.assertEqual(len(self.widget.verified_symbols), 3)
            
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
            self.widget.scanner.start.assert_called()
            print("  Scanner started successfully")
            
            self.assertEqual(self.widget.stack.currentIndex(), 4)
            self.assertEqual(self.widget.dashboard_status.text(), "RUNNING")
            
        print("✅ Full Pipeline Flow Verified")

if __name__ == '__main__':
    unittest.main()
