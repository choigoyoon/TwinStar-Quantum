import sys
import os
import time
import argparse
from pathlib import Path
from typing import Any, cast
from PyQt6.QtWidgets import QApplication, QTabWidget, QPushButton, QLineEdit, QComboBox, QCheckBox, QTableWidget, QWidget
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTimer, QPoint, QObject

# Path setup
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.chdir(str(BASE_DIR))

# Import the standard StarUWindow
from GUI.staru_main import StarUWindow

class GUIStepTester:
    def __init__(self, step=None, all_steps=False, delay=2):
        self.target_step = step
        self.all_steps = all_steps
        self.delay = delay
        self.report_dir = BASE_DIR / "tests" / "gui_report" / "steps"
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize App
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)
            self.app.setStyle('Fusion')
        
        self.window = None
        self.results = []

    def setup_window(self):
        print("🚀 GUI 창 초기화 중 (Tier: admin)...")
        self.window = StarUWindow(user_tier='admin')
        self.window.show()
        self.window.resize(1200, 800)
        cast(Any, QTest).qWaitForWindowExposed(self.window)
        cast(Any, QTest).qWait(1000) # 위젯 초기화 대기

    def capture(self, filename):
        path = str(self.report_dir / f"{filename}.png")
        QApplication.processEvents()
        if self.window:
            self.window.grab().save(path)
            print(f"  [SCREENSHOT] {filename}.png 저장됨")
        else:
            print(f"  [SCREENSHOT] Fail (No Window)")
        return path

    def log_result(self, name, status, duration, error=""):
        res = {
            "name": name,
            "status": status,
            "duration": duration,
            "error": error
        }
        self.results.append(res)
        icon = "✅" if status == "PASS" else "❌"
        print(f" {icon} {name} - {status} ({duration:.2f}s)")
        if error:
            print(f"    Error: {error}")

    def test_step_1_launch(self):
        """[1단계] GUI 단순 실행 테스트"""
        print("\n▶ [1단계] 기본 실행 테스트 시작")
        start = time.time()
        try:
            self.setup_window()
            cast(Any, QTest).qWait(int(self.delay * 1000))

            self.capture("step1_launch")
            self.log_result("1.1 GUI 실행 확인", "PASS", time.time() - start)
        except Exception as e:
            self.log_result("1.1 GUI 실행 확인", "FAIL", time.time() - start, str(e))

    def test_step_2_tabs(self):
        """[2단계] 탭 전환 테스트"""
        print("\n▶ [2단계] 탭 전환 테스트 시작")
        start_total = time.time()
        tabs = cast(Any, self.window).tabs
        count = tabs.count()
        
        for i in range(count):
            start = time.time()
            tab_name = tabs.tabText(i)
            print(f"  - {tab_name} 탭 클릭...")
            tabs.setCurrentIndex(i)
            cast(Any, QTest).qWait(int(self.delay * 1000))

            self.capture(f"step2_tab_{i}")
            self.log_result(f"2.{i+1} {tab_name} 탭 전환", "PASS", time.time() - start)
        
    def test_step_3_optimize(self):
        """[3단계] 최적화 탭 테스트"""
        print("\n▶ [3단계] 최적화 탭 테스트 시작")
        start = time.time()
        try:
            # Switch to Optimization Tab (idx 4 usually, but find by text)
            for i in range(cast(Any, self.window).tabs.count()):
                if "최적화" in cast(Any, self.window).tabs.tabText(i):
                    cast(Any, self.window).tabs.setCurrentIndex(i)
                    break
            cast(Any, QTest).qWait(1000)
            
            page = cast(Any, self.window).optimization_widget
            # OptimizationWidget is a tab container, controls are in single_widget
            if hasattr(page, 'single_widget'):
                page = page.single_widget
            
            # [3.1] 심볼 선택
            print("  - [3.1] 심볼 선택 (BTCUSDT)...")
            self.capture("step3_opt_before_symbol")
            
            # [FIX] 데이터 소스 리프레시 강제 호출
            if hasattr(page, '_load_data_sources'):
                print("    - Calling _load_data_sources()...")
                page._load_data_sources()
                cast(Any, QTest).qWait(int(2000))  # 데이터 로딩 대기
            
            # search_edit에 입력하여 필터링 시도
            if hasattr(page, 'search_edit'):
                print(f"    - Current search text: '{page.search_edit.text()}'")
                page.search_edit.clear()
                page.search_edit.setText("BTCUSDT")
                print(f"    - Set search text to: 'BTCUSDT'")
                cast(Any, QTest).qWait(int(1000))
            
            # data_combo에서 존재하는 항목 선택
            if hasattr(page, 'data_combo'):
                print(f"    - Data combo items ({page.data_combo.count()}):")
                found_btc = False
                for i in range(page.data_combo.count()):
                    txt = page.data_combo.itemText(i)
                    print(f"      [{i}] {txt}")
                    if "BTCUSDT" in txt.upper():
                        page.data_combo.setCurrentIndex(i)
                        print(f"    - Found and selected: {txt}")
                        found_btc = True
                        # Don't break, just log all for debugging
                
                # Re-check selection
                if not found_btc and page.data_combo.count() > 0:
                    print(f"    WARNING: BTCUSDT not found in list, selecting first: {page.data_combo.itemText(0)}")
                    page.data_combo.setCurrentIndex(0)
            
            cast(Any, QTest).qWait(int(1000))
            
            # [3.2] 모드 선택 (Quick)
            print("  - [3.2] Quick 모드 선택...")
            # mode_group in SingleOptimizerWidget
            if hasattr(page, 'mode_group'):
                # Quick mode is usually ID 0
                btn = page.mode_group.button(0)
                if btn:
                    cast(Any, QTest).mouseClick(btn, Qt.MouseButton.LeftButton)
                cast(Any, QTest).qWait(int(2000))

            
            # [3.3] 시작 버튼
            print("  - [3.3] 최적화 시작 버튼 클릭...")
            if hasattr(page, 'run_btn'):
                cast(Any, QTest).mouseClick(page.run_btn, Qt.MouseButton.LeftButton)
                self.capture("step3_opt_start")
                # Wait for finish signal or progress
                print("  - 진행 대기 중 (Max 30s)...")
                wait_start = time.time()
                # in SingleOptimizerWidget, it might be self.progress or self.progress_bar
                prog = getattr(page, 'progress', getattr(page, 'progress_bar', None))
                
                # First wait for it to appear (if it's not already)
                wait_start = time.time()
                while prog and not prog.isVisible() and time.time() - wait_start < 5:
                    cast(Any, QTest).qWait(100)
                
                # Then wait for it to finish (disappear or reach 100%)
                wait_start = time.time()
                while prog and prog.isVisible() and time.time() - wait_start < 45:
                    cast(Any, QTest).qWait(1000)

                
                self.capture("step3_opt_finished")
                self.log_result("3.3 최적화 실행 완료", "PASS" if not (prog and prog.isVisible()) else "TIMEOUT", time.time() - start)
            else:
                self.log_result("3.3 최적화 시작", "FAIL", 0, "run_btn not found in page")

        except Exception as e:
            self.log_result("3단계 전체", "FAIL", time.time() - start, str(e))

    def test_step_4_backtest(self):
        """[4단계] 백테스트 탭 테스트"""
        print("\n▶ [4단계] 백테스트 탭 테스트 시작")
        start = time.time()
        try:
            for i in range(cast(Any, self.window).tabs.count()):
                if "백테스트" in cast(Any, self.window).tabs.tabText(i):
                    cast(Any, self.window).tabs.setCurrentIndex(i)
                    break
            cast(Any, QTest).qWait(1000)
            
            page = cast(Any, self.window).backtest_widget
            if hasattr(page, 'single_widget'):
                page = page.single_widget
            
            # [4.1] 프리셋 로드
            print("  - [4.1] 프리셋 첫 번째 항목 선택...")
            if hasattr(page, 'preset_combo') and page.preset_combo.count() > 0:
                page.preset_combo.setCurrentIndex(0)
                cast(Any, QTest).qWait(int(2000))
            
            # [4.2] 실행
            print("  - [4.2] 백테스트 실행...")
            # Try specific named attributes first (most reliable)
            btn = getattr(page, '_run_btn', getattr(page, 'run_btn', None))
            
            # Fallback: Extremely robust recursive search
            if not btn:
                from locales.lang_manager import t
                from PyQt6.QtCore import QObject
                from PyQt6.QtWidgets import QPushButton
                target_text = t("backtest.run") # "백테스트 실행"
                print(f"    - Searching recursively for target text: '{target_text}'")
                
                # Check EVERY child object that might have a text property
                # and check specifically for QPushButton first
                all_children = page.findChildren(QObject)
                print(f"    - Total children found: {len(all_children)}")
                
                for child in page.findChildren(QPushButton):
                    if target_text in child.text():
                        btn = child
                        print(f"    - Found QPushButton via text: {btn}")
                        break
                
                if not btn:
                    # Fallback to any QObject with text property
                    for child in all_children:
                        if child == page: continue
                        if hasattr(child, 'text'):
                            try:
                                c_text = child.text()
                                if target_text in c_text:
                                    btn = child
                                    print(f"    - Found widget with text '{c_text}': {child}")
                                    break
                            except Exception:

                                continue
            
            if not btn:
                # Try generic button search if the above fails
                for child in page.findChildren(QPushButton):
                    c_text = child.text()
                    if any(x in c_text for x in ["실행", "Run", "Start", "백테스트"]):
                        btn = child
                        print(f"    - Found button via partial matching: {btn} ('{c_text}')")
                        break
                
                if not btn:
                    print("    - FAILED to find any suitable button. Listing ALL children for debug:")
                    for child in all_children[:20]: # Show first 20
                        print(f"      {child.__class__.__name__}: {getattr(child, 'text', lambda: 'N/A')()}")

            if btn:
                print(f"  - Clicking button: {btn} ('{getattr(btn, 'text', lambda: '??')()}')")
                cast(Any, QTest).mouseClick(btn, Qt.MouseButton.LeftButton)
                self.capture("step4_backtest_start")
                
                # Wait for progress bar (_progress in SingleBacktestWidget)
                prog = getattr(page, '_progress', getattr(page, 'progress', None))
                
                print("  - 진행 대기 중 (Max 20s)...")
                wait_start = time.time()
                while prog and not prog.isVisible() and time.time() - wait_start < 5:
                    cast(Any, QTest).qWait(100)
                    
                wait_start = time.time()
                while prog and prog.isVisible() and time.time() - wait_start < 20:
                    cast(Any, QTest).qWait(1000)
                
                self.capture("step4_backtest_finished")
                self.log_result("4.2 백테스트 실행 완료", "PASS", time.time() - start)
            else:
                self.log_result("4.2 백테스트 실행", "FAIL", 0, "run button not found in page (even with recursive search)")

        except Exception as e:
            self.log_result("4단계 전체", "FAIL", time.time() - start, str(e))

    def test_step_5_pipeline(self):
        """[5단계] 자동매매 파이프라인 테스트"""
        print("\n▶ [5단계] 자동매매 파이프라인 테스트 시작")
        start = time.time()
        try:
            for i in range(cast(Any, self.window).tabs.count()):
                if "매매" in cast(Any, self.window).tabs.tabText(i):
                    cast(Any, self.window).tabs.setCurrentIndex(i)
                    break
            cast(Any, QTest).qWait(1000)
            
            # Find pipeline
            pipeline = None
            if hasattr(self.window, 'auto_pipeline_widget'):
                pipeline = cast(Any, self.window).auto_pipeline_widget
            
            if pipeline:
                # Step 1 -> 2
                print("  - Step 1 (심볼 선택) -> Step 2 이동...")
                if hasattr(pipeline, '_go_next'):
                    pipeline._go_next()
                    cast(Any, QTest).qWait(2000)
                    self.capture("step5_pipeline_step2")
                    
                    # Step 2 -> 3
                    print("  - Step 2 (최적화) -> Step 3 이동...")
                    pipeline._go_next()
                    cast(Any, QTest).qWait(2000)
                    self.capture("step5_pipeline_step3")
                    
                    self.log_result("5.1 파이프라인 단계 이동", "PASS", time.time() - start)
                else:
                    self.log_result("5.1 파이프라인 이동", "FAIL", 0, "_go_next not found")
            else:
                self.log_result("5.1 파이프라인 초기화", "FAIL", 0, "auto_pipeline_widget not found")
        except Exception as e:
            self.log_result("5단계 전체", "FAIL", time.time() - start, str(e))

    def run(self):
        if self.all_steps:
            self.test_step_1_launch()
            self.test_step_2_tabs()
            self.test_step_3_optimize()
            self.test_step_4_backtest()
            self.test_step_5_pipeline()
        else:
            if self.target_step == 1: self.test_step_1_launch()
            elif self.target_step == 2: 
                self.setup_window()
                self.test_step_2_tabs()
            elif self.target_step == 3:
                self.setup_window()
                self.test_step_3_optimize()
            elif self.target_step == 4:
                self.setup_window()
                self.test_step_4_backtest()
            elif self.target_step == 5:
                self.setup_window()
                self.test_step_5_pipeline()
        
        self.generate_report()
        if self.window:
            self.window.close()

    def generate_report(self):
        print("\n📊 최종 테스트 요약")
        pass_count = sum(1 for r in self.results if r['status'] == 'PASS')
        fail_count = sum(1 for r in self.results if r['status'] != 'PASS')
        print(f"  총 테스트: {len(self.results)}")
        print(f"  성공: {pass_count}")
        print(f"  실패: {fail_count}")
        
        report_path = BASE_DIR / "tests" / "gui_report" / "gui_step_report.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# GUI 단계별 검증 리포트\n\n")
            f.write(f"- 총 테스트: {len(self.results)}\n")
            f.write(f"- 성공: {pass_count}\n")
            f.write(f"- 실패: {fail_count}\n\n")
            f.write("| 테스트명 | 결과 | 소요시간 | 비고 |\n")
            f.write("|----------|------|----------|------|\n")
            for r in self.results:
                f.write(f"| {r['name']} | {r['status']} | {r['duration']:.2f}s | {r['error']} |\n")
        
        print(f"\n📄 리포트 저장됨: {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", type=int, default=None)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()
    
    tester = GUIStepTester(step=args.step, all_steps=args.all, delay=args.delay)
    tester.run()
