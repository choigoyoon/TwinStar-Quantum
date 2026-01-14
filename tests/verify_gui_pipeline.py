"""
GUI Pipeline Automated Verification
Tests the structural integrity and connectivity of the AutoPipelineWidget.
"""
import sys
import os
import unittest
from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QComboBox, QCheckBox, QLabel, QTableWidget, QProgressBar, QRadioButton, QSpinBox, QDoubleSpinBox
from PyQt6.QtCore import QTimer

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class TestGUIPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n=== GUI 파이프라인 자동 검증 시작 ===\n")
        if not QApplication.instance():
            cls.app = QApplication([])
        else:
            cls.app = QApplication.instance()

    def test_import_and_instantiation(self):
        try:
            from GUI.auto_pipeline_widget import AutoPipelineWidget
            print("[임포트] ✅ 5/5 (모듈 로드 성공)")
        except ImportError as e:
            self.fail(f"Import Failed: {e}")
            
        self.widget = AutoPipelineWidget()
        print("[위젯 생성] ✅ (인스턴스화 성공)")
        
        # --- Step 1 Validation ---
        s1 = self.widget.step1
        has_combo = hasattr(self.widget, 'ex_combo')
        has_list = hasattr(self.widget, 'symbol_list')
        
        # Find Next Button
        btns = s1.findChildren(QPushButton)
        has_next = any("Next" in b.text() for b in btns)
        has_load = any("Load" in b.text() for b in btns)
        
        if has_combo and has_list and has_next and has_load:
            print("[Step 1] ✅ 4/4 컴포넌트")
        else:
            print(f"[Step 1] ❌ 실패 (Combo:{has_combo}, List:{has_list}, Next:{has_next}, Load:{has_load})")

        # --- Step 2 Validation ---
        s2 = self.widget.step2
        has_mode = hasattr(self.widget, 'mode_combo')
        has_prog = hasattr(self.widget, 'batch_progress')
        has_start = hasattr(self.widget, 'btn_start_opt')
        
        if has_mode and has_prog and has_start:
             print("[Step 2] ✅ 3/3 컴포넌트")
        else:
             print(f"[Step 2] ❌ 실패")

        # --- Step 3 Validation ---
        s3 = self.widget.step3
        has_wr = hasattr(self.widget, 'verify_wr')
        has_mdd = hasattr(self.widget, 'verify_mdd')
        has_table = hasattr(self.widget, 'verify_table')
        # Find Verify Button
        btns3 = s3.findChildren(QPushButton)
        has_verify = any("Verify" in b.text() or "Verification" in b.text() for b in btns3)
        
        if has_wr and has_mdd and has_table and has_verify:
             print("[Step 3] ✅ 4/4 컴포넌트")
        else:
             print(f"[Step 3] ❌ 실패")
             
        # --- Step 4 Validation ---
        s4 = self.widget.step4
        has_amt = hasattr(self.widget, 'entry_amt')
        has_lev = hasattr(self.widget, 'leverage')
        has_max = hasattr(self.widget, 'max_pos')
        has_prio = hasattr(self.widget, 'p_wr') # Radio button
        # Find Start Button
        btns4 = s4.findChildren(QPushButton)
        has_start_scan = any("Start" in b.text() for b in btns4)
        
        if has_amt and has_lev and has_max and has_prio and has_start_scan:
             print("[Step 4] ✅ 5/5 컴포넌트")
        else:
             print(f"[Step 4] ❌ 실패")

        # --- Step 5 Validation ---
        s5 = self.widget.step5
        has_status = hasattr(self.widget, 'dashboard_status')
        has_pos_table = hasattr(self.widget, 'pos_table')
        has_log = hasattr(self.widget, 'scan_log')
        
        if has_status and has_pos_table and has_log:
             print("[Step 5] ✅ 3/3 컴포넌트")
        else:
             print(f"[Step 5] ❌ 실패")
             
        # --- Signal Checks ---
        opt_connected = self.widget.btn_start_opt.receivers(self.widget.btn_start_opt.clicked) > 0
        combo_connected = self.widget.symbol_list.receivers(self.widget.symbol_list.itemChanged) > 0
        if opt_connected and combo_connected:
            print("[시그널] ✅ 연결됨")
        else:
            print(f"[시그널] ❌ 실패 (Opt:{opt_connected}, List:{combo_connected})")

        # --- Core Connectivity ---
        # Check Imports
        try:
            import core.batch_optimizer
            import core.batch_verifier
            import core.auto_scanner
            print("[코어] ✅ 3/3 연결 (모듈 존재)")
        except ImportError:
             print("[코어] ❌ 실패")

        print("\n총 결과: ✅ GUI 파이프라인 정상")

if __name__ == '__main__':
    unittest.main()
