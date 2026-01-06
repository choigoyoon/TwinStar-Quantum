import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from GUI.auto_pipeline_widget import AutoPipelineWidget
from core.auto_scanner import AutoScanner
from utils.preset_manager import get_preset_manager

class TestAutoPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def setUp(self):
        self.widget = AutoPipelineWidget()
        
    def test_step_navigation(self):
        """Verify navigation between 5 steps"""
        self.assertEqual(self.widget.stack.currentIndex(), 0) # Step 1
        
        self.widget._go_next()
        self.assertEqual(self.widget.stack.currentIndex(), 1) # Step 2
        
        self.widget._go_next()
        self.assertEqual(self.widget.stack.currentIndex(), 2) # Step 3
        
        self.widget._go_next()
        self.assertEqual(self.widget.stack.currentIndex(), 3) # Step 4
        
        self.widget._go_next()
        self.assertEqual(self.widget.stack.currentIndex(), 4) # Step 5

    @patch('PyQt5.QtWidgets.QMessageBox')
    @patch('core.auto_scanner.AutoScanner')
    def test_scanner_start(self, mock_scanner_cls, mock_msgbox):
        """Verify scanner starts with correct config"""
        # Mocking
        mock_instance = mock_scanner_cls.return_value
        self.widget.scanner = mock_instance
        
        # Go to Step 4
        self.widget.stack.setCurrentIndex(3)
        
        # Set UI values
        self.widget.entry_amt.setValue(500)
        self.widget.leverage.setValue(5)
        self.widget.max_pos.setValue(3)
        
        # Start
        self.widget._start_scanner()
        
        # Verify Config
        expected_config = {
            'entry_amount': 500.0,
            'leverage': 5,
            'max_positions': 3,
            'priority': 'win_rate',
            'blacklist': [],
            'interval': 1.5
        }
        
        # Verify calls
        mock_instance.set_config.assert_called_with(expected_config)
        mock_instance.load_verified_symbols.assert_called_once()
        mock_instance.start.assert_called_once()
        
        # Check transition to Step 5
        self.assertEqual(self.widget.stack.currentIndex(), 4)
        self.assertEqual(self.widget.dashboard_status.text(), "RUNNING")

    @patch('PyQt5.QtWidgets.QMessageBox')
    def test_preset_verification_flow(self, mock_msgbox):
        """Verify verification flow updates verified_symbols"""
        self.widget.selected_symbols = ["BTCUSDT", "ETHUSDT"]
        
        # Mock BatchVerifier
        with patch('core.batch_verifier.BatchVerifier') as MockVerifier:
            verifier = MockVerifier.return_value
            verifier.verify_presets.return_value = [
                {'symbol': 'BTCUSDT', 'win_rate': 80, 'mdd': 10, 'passed': True},
                {'symbol': 'ETHUSDT', 'win_rate': 60, 'mdd': 25, 'passed': False}
            ]
            
            # Run
            self.widget._run_verification()
            
            # Check Result
            self.assertEqual(len(self.widget.verified_symbols), 1)
            self.assertEqual(self.widget.verified_symbols[0], "BTCUSDT")

if __name__ == '__main__':
    unittest.main()
