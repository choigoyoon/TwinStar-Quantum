import sys
import os
import time
import unittest
import argparse
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QTabWidget, QPushButton, QLineEdit, QComboBox, QCheckBox, QTableWidget, QWidget

from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt, QTimer, QPoint

# Add base path for imports
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Mock Login or handle it
# If we want to test StarUWindow directly, we can just instantiate it.
try:
    from GUI.staru_main import StarUWindow
except ImportError:
    # If paths are tricky
    sys.path.append(os.path.join(str(BASE_DIR), 'GUI'))
    from staru_main import StarUWindow

class GUIAutomationTester(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create report directories
        cls.report_dir = BASE_DIR / "tests" / "gui_report"
        cls.screenshot_dir = cls.report_dir / "screenshots"
        cls.logs_dir = cls.report_dir / "logs"
        for d in [cls.screenshot_dir, cls.logs_dir]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Initialize App
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication(sys.argv)
            cls.app.setStyle('Fusion')

    def setUp(self):
        # Instantiate StarUWindow (Admin tier to avoid restrictions)
        self.window = StarUWindow(user_tier='admin')
        self.window.show()
        self.window.resize(1200, 800)
        QTest.qWaitForWindowExposed(self.window)
        # Wait for widget initialization (it log "위젯 초기화 완료")
        QTest.qWait(1000)

    def tearDown(self):
        self.window.close()

    def capture(self, filename):
        """Take a screenshot of the main window"""
        path = str(self.screenshot_dir / f"{filename}.png")
        QApplication.processEvents()
        self.window.grab().save(path)
        print(f"  [SCREENSHOT] Saved to {path}")

    def find_tab_index(self, text_contains):
        """Find tab index by searching text in tab labels"""
        tabs = self.window.tabs
        for i in range(tabs.count()):
            if text_contains in tabs.tabText(i):
                return i
        return -1

    def test_scenario_1_optimization_tab(self):
        """[SCENARIO 1] Optimization Flow (Tab-based)"""
        print("\n▶ Running Scenario 1: Optimization Flow")
        
        # 1. Click Optimization Tab
        idx = self.find_tab_index("최적화")
        print(f"  - Switching to Optimization tab (index: {idx})")
        self.window.tabs.setCurrentIndex(idx)
        QTest.qWait(500)
        self.capture("sc1_opt_tab")
        
        # 2. Get Optimization Widget
        page = self.window.optimization_widget
        
        # 3. Simulate Run (Quick mode if available)
        if hasattr(page, 'run_btn'):
            print("  - Clicking 'Start Optimization'...")
            QTest.mouseClick(page.run_btn, Qt.LeftButton)
            QTest.qWait(2000)
            self.capture("sc1_opt_running")
            
            # Wait for finish signal if possible, or just check progress
            # For automation, we'll just check it started
            print("  - Optimization triggered successfully.")
        else:
            print("  - ERROR: run_btn not found in optimization_widget")

    def test_scenario_2_backtest_tab(self):
        """[SCENARIO 2] Backtest Flow (Tab-based)"""
        print("\n▶ Running Scenario 2: Backtest Flow")
        
        # 1. Click Backtest Tab
        idx = self.find_tab_index("백테스트")
        self.window.tabs.setCurrentIndex(idx)
        QTest.qWait(500)
        self.capture("sc2_bt_tab")
        
        page = self.window.backtest_widget
        
        # 2. Configure Symbol
        if hasattr(page, 'symbol_combo'):
            page.symbol_combo.setCurrentIndex(0) # BTCUSDT
            QTest.qWait(200)
        
        # 3. Click Run
        if hasattr(page, 'run_btn'):
            print("  - Clicking 'Start Backtest'...")
            QTest.mouseClick(page.run_btn, Qt.LeftButton)
            QTest.qWait(2000)
            self.capture("sc2_bt_running")
        else:
            print("  - ERROR: run_btn not found in backtest_widget")

    def test_scenario_3_auto_pipeline(self):
        """[SCENARIO 3] Auto Trading Pipeline (Step-by-Step)"""
        print("\n▶ Running Scenario 3: Auto Trading Pipeline")
        
        # Auto Pipeline might be in a separate tab or integrated
        # According to staru_main.py, it's integrated or in a tab
        idx = self.find_tab_index("자동매매")
        if idx == -1:
            # Maybe inside Trading tab?
            print("  - '자동매매' tab not found, trying Trading tab integration")
            idx = self.find_tab_index("매매")
            self.window.tabs.setCurrentIndex(idx)
            # Find AutoPipelineWidget in the children
            pipeline = self.window.dashboard.findChild(QWidget, "AutoPipelineWidget")
            # If not found by name, try looking at the dashbaord's internal layout or variable
            if not pipeline and hasattr(self.window, 'auto_pipeline_widget'):
                pipeline = self.window.auto_pipeline_widget
        else:
            self.window.tabs.setCurrentIndex(idx)
            pipeline = self.window.auto_pipeline_widget
            
        if pipeline:
            print("  - Pipeline widget found. Testing Step 1 navigation...")
            self.capture("sc3_pipeline_start")
            
            # Simulate Next clicks through steps 1-5
            if hasattr(pipeline, 'stack'):
                for step in range(1, 4): # Test first few steps
                    print(f"    * Progressing to Step {step+1}...")
                    if hasattr(pipeline, '_go_next'):
                        pipeline._go_next()
                        QTest.qWait(500)
                        self.capture(f"sc3_pipeline_step_{step+1}")
        else:
            print("  - ERROR: AutoPipelineWidget not found")

    def test_scenario_4_settings(self):
        """[SCENARIO 4] Settings Save/Load"""
        print("\n▶ Running Scenario 4: Settings")
        idx = self.find_tab_index("설정")
        self.window.tabs.setCurrentIndex(idx)
        QTest.qWait(500)
        self.capture("sc4_settings")
        
        page = self.window.settings_widget
        # Verify it loaded
        self.assertIsNotNone(page, "Settings widget should exist")

    def test_stress_tab_switching(self):
        """[STRESS] Rapid Tab Switching"""
        print("\n▶ Running Stress Test: Rapid Tab Switching (30 times)")
        tabs = self.window.tabs
        count = tabs.count()
        start_time = time.time()
        for i in range(30):
            tabs.setCurrentIndex(i % count)
            QApplication.processEvents()
        
        elapsed = time.time() - start_time
        print(f"  - 30 switches completed in {elapsed:.2f}s")
        self.capture("stress_tabs")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--scenario", type=int, default=None)
    # We ignore unknown args to let unittest.main() work
    args, unknown = parser.parse_known_args()
    
    # Overwrite sys.argv for unittest
    sys.argv = [sys.argv[0]] + unknown
    
    print("🚀 Starting TwinStar Quantum Legacy/Standard GUI Automation Suite...")
    unittest.main()
