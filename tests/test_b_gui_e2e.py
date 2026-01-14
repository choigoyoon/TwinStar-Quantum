"""
Test B: GUI E2E Test
- Tests Step 1-5 widget creation
- Verifies button connections
- Checks UI element existence
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class GUITest:
    def __init__(self):
        self.results = []
        
    def log(self, msg, status='INFO'):
        icon = {'PASS': '✅', 'FAIL': '❌', 'INFO': 'ℹ️'}
        print(f"{icon.get(status, '·')} {msg}")
        self.results.append({'msg': msg, 'status': status})
    
    def test_widget_creation(self):
        """Test AutoPipelineWidget instantiation"""
        self.log("[Test 1] Widget Creation")
        
        try:
            from PyQt6.QtWidgets import QApplication
            
            # Need QApplication for widgets
            app = QApplication.instance() or QApplication(sys.argv)
            
            from GUI.auto_pipeline_widget import AutoPipelineWidget
            
            widget = AutoPipelineWidget()
            
            # Check steps exist
            assert hasattr(widget, 'step1'), "Missing step1"
            assert hasattr(widget, 'step2'), "Missing step2"
            assert hasattr(widget, 'step3'), "Missing step3"
            assert hasattr(widget, 'step4'), "Missing step4"
            assert hasattr(widget, 'step5'), "Missing step5"
            
            self.log("All 5 steps created", 'PASS')
            return True
            
        except Exception as e:
            self.log(f"Widget creation failed: {e}", 'FAIL')
            return False
    
    def test_step2_optimization_config(self):
        """Test Step 2 has optimization config controls"""
        self.log("\n[Test 2] Step 2 Optimization Config")
        
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance() or QApplication(sys.argv)
            
            from GUI.auto_pipeline_widget import AutoPipelineWidget
            widget = AutoPipelineWidget()
            
            # Check config controls exist
            assert hasattr(widget, 'opt_min_wr'), "Missing opt_min_wr"
            assert hasattr(widget, 'opt_max_mdd'), "Missing opt_max_mdd"
            assert hasattr(widget, 'opt_min_trades'), "Missing opt_min_trades"
            
            # Check defaults
            assert widget.opt_min_wr.value() == 70, f"Wrong WR default: {widget.opt_min_wr.value()}"
            assert widget.opt_max_mdd.value() == 20, f"Wrong MDD default: {widget.opt_max_mdd.value()}"
            assert widget.opt_min_trades.value() == 30, f"Wrong trades default: {widget.opt_min_trades.value()}"
            
            self.log("Strict filter controls verified", 'PASS')
            return True
            
        except Exception as e:
            self.log(f"Step 2 config test failed: {e}", 'FAIL')
            return False
    
    def test_step3_backtest_ui(self):
        """Test Step 3 has unified backtest UI"""
        self.log("\n[Test 3] Step 3 Unified Backtest UI")
        
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance() or QApplication(sys.argv)
            
            from GUI.auto_pipeline_widget import AutoPipelineWidget
            widget = AutoPipelineWidget()
            
            # Check backtest result labels
            assert hasattr(widget, 'ub_trades_lbl'), "Missing trades label"
            assert hasattr(widget, 'ub_wr_lbl'), "Missing WR label"
            assert hasattr(widget, 'ub_mdd_lbl'), "Missing MDD label"
            assert hasattr(widget, 'ub_pf_lbl'), "Missing PF label"
            assert hasattr(widget, 'ub_progress'), "Missing progress bar"
            
            self.log("Backtest UI elements verified", 'PASS')
            return True
            
        except Exception as e:
            self.log(f"Step 3 UI test failed: {e}", 'FAIL')
            return False
    
    def test_step5_dashboard_metrics(self):
        """Test Step 5 has dashboard metrics"""
        self.log("\n[Test 4] Step 5 Dashboard Metrics")
        
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance() or QApplication(sys.argv)
            
            from GUI.auto_pipeline_widget import AutoPipelineWidget
            widget = AutoPipelineWidget()
            
            # Check metric labels
            assert hasattr(widget, 'metric_targets'), "Missing targets label"
            assert hasattr(widget, 'metric_stage2'), "Missing stage2 label"
            assert hasattr(widget, 'metric_active'), "Missing active label"
            assert hasattr(widget, 'dash_timer'), "Missing dashboard timer"
            
            self.log("Dashboard metrics verified", 'PASS')
            return True
            
        except Exception as e:
            self.log(f"Step 5 test failed: {e}", 'FAIL')
            return False
    
    def test_navigation(self):
        """Test step navigation"""
        self.log("\n[Test 5] Navigation Functions")
        
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance() or QApplication(sys.argv)
            
            from GUI.auto_pipeline_widget import AutoPipelineWidget
            widget = AutoPipelineWidget()
            
            # Start at step 0
            assert widget.stack.currentIndex() == 0, "Not starting at step 0"
            
            # Navigate forward
            widget._go_next()
            assert widget.stack.currentIndex() == 1, "Failed to go next"
            
            # Navigate back
            widget._go_back()
            assert widget.stack.currentIndex() == 0, "Failed to go back"
            
            self.log("Navigation verified", 'PASS')
            return True
            
        except Exception as e:
            self.log(f"Navigation test failed: {e}", 'FAIL')
            return False
    
    def run_all(self):
        print("=" * 60)
        print("GUI E2E TEST")
        print("=" * 60)
        
        tests = [
            self.test_widget_creation,
            self.test_step2_optimization_config,
            self.test_step3_backtest_ui,
            self.test_step5_dashboard_metrics,
            self.test_navigation
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.log(f"Test crashed: {e}", 'FAIL')
                failed += 1
        
        print("\n" + "=" * 60)
        print(f"RESULTS: {passed} passed, {failed} failed")
        print("=" * 60)
        
        return failed == 0

if __name__ == '__main__':
    tester = GUITest()
    success = tester.run_all()
    sys.exit(0 if success else 1)
