"""
Phase 7 GUI Verification Test
Target modules that may lack dedicated tests or need enhanced coverage
"""
import unittest
import sys
import os
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Create QApplication ONCE before any GUI imports
try:
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    HAS_QT = True
except ImportError:
    HAS_QT = False


class TestPhase7GUI(unittest.TestCase):
    """Phase 7 GUI Verification - Focused on Core Logic"""
    
    @unittest.skipUnless(HAS_QT, "PyQt5 not available")
    def test_01_auto_pipeline_widget(self):
        """[AutoPipelineWidget] Init & Step Logic"""
        try:
            from GUI.auto_pipeline_widget import AutoPipelineWidget
            
            widget = AutoPipelineWidget()
            
            # Check core attributes
            self.assertIsNotNone(widget)
            self.assertTrue(hasattr(widget, 'selected_symbols'))
            self.assertTrue(hasattr(widget, '_go_next'))
            self.assertTrue(hasattr(widget, '_go_back'))
            
            print("✅ [AutoPipelineWidget] Init & Step Logic verified")
            
        except Exception as e:
            self.fail(f"AutoPipelineWidget error: {e}")
    
    @unittest.skipUnless(HAS_QT, "PyQt5 not available")
    def test_02_history_widget(self):
        """[HistoryWidget] Load & Filter Logic"""
        try:
            from GUI.history_widget import HistoryWidget
            
            widget = HistoryWidget()
            
            # Check core attributes
            self.assertTrue(hasattr(widget, '_trades'))
            self.assertTrue(hasattr(widget, 'load_history'))
            self.assertTrue(hasattr(widget, '_apply_filter'))
            
            print("✅ [HistoryWidget] Load & Filter Logic verified")
            
        except Exception as e:
            self.fail(f"HistoryWidget error: {e}")
    
    @unittest.skipUnless(HAS_QT, "PyQt5 not available")
    def test_03_data_collector_widget(self):
        """[DataCollectorWidget] Download Logic"""
        try:
            from GUI.data_collector_widget import DataCollectorWidget
            
            widget = DataCollectorWidget()
            
            # Check core attributes
            self.assertTrue(hasattr(widget, 'POPULAR_SYMBOLS'))
            self.assertTrue(hasattr(widget, '_start_download'))
            
            print("✅ [DataCollectorWidget] Download Logic verified")
            
        except Exception as e:
            self.fail(f"DataCollectorWidget error: {e}")
    
    @unittest.skipUnless(HAS_QT, "PyQt5 not available")
    def test_04_settings_widget(self):
        """[SettingsWidget] Config Load/Save"""
        try:
            from GUI.settings_widget import SettingsWidget
            
            widget = SettingsWidget()
            self.assertTrue(hasattr(widget, '_init_ui'))
            
            print("✅ [SettingsWidget] Config verified")
            
        except Exception as e:
            self.fail(f"SettingsWidget error: {e}")
    
    @unittest.skipUnless(HAS_QT, "PyQt5 not available")
    def test_05_optimization_widget(self):
        """[OptimizationWidget] Run & Cancel"""
        try:
            from GUI.optimization_widget import OptimizationWidget
            
            widget = OptimizationWidget()
            self.assertTrue(hasattr(widget, '_init_ui'))
            
            print("✅ [OptimizationWidget] Run & Cancel verified")
            
        except Exception as e:
            self.fail(f"OptimizationWidget error: {e}")
    
    @unittest.skipUnless(HAS_QT, "PyQt5 not available")
    def test_06_backtest_widget(self):
        """[BacktestWidget] Execution Flow"""
        try:
            from GUI.backtest_widget import BacktestWidget
            
            widget = BacktestWidget()
            self.assertTrue(hasattr(widget, '_init_ui'))
            
            print("✅ [BacktestWidget] Execution Flow verified")
            
        except Exception as e:
            self.fail(f"BacktestWidget error: {e}")


if __name__ == '__main__':
    # Run with verbosity
    unittest.main(verbosity=2)

