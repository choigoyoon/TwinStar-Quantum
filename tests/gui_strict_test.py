#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Strict GUI Test - 에러 감지 강화 버전
- 모든 에러 캡처 및 즉시 중단
- 위젯 상태 실제 검증
- 상세 로그 출력
"""

import sys
import os
import io
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, cast

# 프로젝트 루트 설정
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "GUI"))
os.chdir(PROJECT_ROOT)

# 에러 캡처용 핸들러
class ErrorCapture:
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def add_error(self, msg):
        self.errors.append(msg)
        
    def add_warning(self, msg):
        self.warnings.append(msg)
        
    def has_errors(self):
        return len(self.errors) > 0
    
    def clear(self):
        self.errors.clear()
        self.warnings.clear()

ERROR_CAPTURE = ErrorCapture()

# 커스텀 로깅 핸들러 - ERROR 레벨 캡처 (API 에러는 제외)
class ErrorLoggingHandler(logging.Handler):
    # API/네트워크 에러는 무시 (설정 문제지 코드 문제가 아님)
    IGNORE_PATTERNS = [
        "Balance error",
        "apikey/password",
        "API Secret required",
        "포지션 조회 에러",
        "ConnectionError",
        "Timeout",
    ]
    
    def emit(self, record):
        msg = record.getMessage()
        
        # 무시할 에러 패턴 체크
        for pattern in self.IGNORE_PATTERNS:
            if pattern in msg:
                ERROR_CAPTURE.add_warning(f"[API] {msg[:100]}")
                return
                
        if record.levelno >= logging.ERROR:
            ERROR_CAPTURE.add_error(f"[{record.name}] {msg}")
        elif record.levelno >= logging.WARNING:
            ERROR_CAPTURE.add_warning(f"[{record.name}] {msg}")

# 루트 로거에 핸들러 추가
logging.getLogger().addHandler(ErrorLoggingHandler())

class StrictTestResult:
    def __init__(self, name):
        self.name = name
        self.passed = False
        self.error: 'str | None' = None
        self.traceback: 'str | None' = None
        self.checks = []
        
    def add_check(self, name, passed, detail=""):
        self.checks.append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            self.passed = False
            
    def set_passed(self):
        self.passed = all(c["passed"] for c in self.checks) if self.checks else True
        
    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        result = f"[{self.name}] {status}\n"
        for c in self.checks:
            check_status = "  → " if c["passed"] else "  ✗ "
            result += f"{check_status}{c['name']}: {'OK' if c['passed'] else 'FAIL'}"
            if c["detail"]:
                result += f" ({c['detail']})"
            result += "\n"
        if self.error:
            result += f"  ⚠ Error: {self.error}\n"
        if self.traceback:
            result += f"  📋 Traceback:\n{self.traceback}\n"
        return result


class StrictGUITest:
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.results = []
        self.app = None
        self.window = None
        self.screenshot_dir = PROJECT_ROOT / "tests" / "gui_report"
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        
    def log(self, msg):
        if self.verbose:
            print(f"  {msg}")
            
    def capture_screenshot(self, name):
        """스크린샷 저장"""
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtGui import QPixmap
            
            if self.window:
                pixmap = QPixmap(cast(Any, self.window).size())
                cast(Any, self.window).render(pixmap)
                path = self.screenshot_dir / f"{name}.png"
                pixmap.save(str(path))
                return str(path)
        except Exception as e:
            self.log(f"Screenshot failed: {e}")
        return None
        
    def check_widget(self, widget, name):
        """위젯 상태 종합 검증"""
        checks = {}
        
        # 1. None 체크
        checks["exists"] = widget is not None
        if not checks["exists"]:
            return checks, f"{name} is None"
            
        # 2. visible 체크
        try:
            checks["visible"] = widget.isVisible()
        except Exception:
            checks["visible"] = False
            
        # 3. enabled 체크
        try:
            checks["enabled"] = widget.isEnabled()
        except Exception:
            checks["enabled"] = False
            
        # 4. 크기 체크
        try:
            size = widget.size()
            checks["has_size"] = size.width() > 0 and size.height() > 0
        except Exception:
            checks["has_size"] = False
            
        all_ok = all(checks.values())
        detail = ", ".join([f"{k}={v}" for k, v in checks.items()])
        
        return checks, detail if not all_ok else "OK"

    def run_step(self, name, func):
        """단계 실행 (에러 캡처)"""
        result = StrictTestResult(name)
        ERROR_CAPTURE.clear()
        
        print(f"\n{'='*50}")
        print(f"[{name}]")
        print('='*50)
        
        try:
            func(result)
            
            # 캡처된 에러 확인
            if ERROR_CAPTURE.has_errors():
                result.add_check("에러 로그 없음", False, 
                    f"{len(ERROR_CAPTURE.errors)}개 에러: {ERROR_CAPTURE.errors[:3]}")
            else:
                result.add_check("에러 로그 없음", True)
                
            result.set_passed()
            
        except Exception as e:
            result.error = str(e)
            result.traceback = traceback.format_exc()
            result.passed = False
            self.capture_screenshot(f"error_{name.replace(' ', '_')}")
            
        self.results.append(result)
        print(result)
        
        return result.passed

    def test_launch(self, result: StrictTestResult):
        """Step 1: GUI 실행 검증"""
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtTest import QTest
        
        self.log("QApplication 생성...")
        self.app = QApplication.instance() or QApplication(sys.argv)
        result.add_check("QApplication 생성", True)
        
        self.log("Staru_main import...")
        try:
            from GUI.staru_main import StarUWindow
            result.add_check("staru_main import", True)
        except Exception as e:
            result.add_check("staru_main import", False, str(e))
            raise
            
        self.log("메인 윈도우 생성...")
        try:
            self.window = StarUWindow(user_tier="admin")
            result.add_check("StarUWindow 생성", True)
        except Exception as e:
            result.add_check("StarUWindow 생성", False, str(e))
            raise
            
        self.log("윈도우 표시...")
        cast(Any, self.window).show()
        cast(Any, QTest).qWait(3000)
        
        # 윈도우 상태 검증
        checks, detail = self.check_widget(self.window, "MainWindow")
        result.add_check("메인 윈도우 상태", all(checks.values()), detail)
        
        # 탭 위젯 검증
        if hasattr(self.window, 'tabs'):
            checks, detail = self.check_widget(cast(Any, self.window).tabs, "TabWidget")
            result.add_check("탭 위젯 상태", all(checks.values()), detail)
            result.add_check("탭 개수", cast(Any, self.window).tabs.count() > 0, 
                f"{cast(Any, self.window).tabs.count()}개")
        else:
            result.add_check("탭 위젯 존재", False, "tabs 속성 없음")
            
        self.capture_screenshot("step1_launch")

    def test_tab_switch(self, result: StrictTestResult):
        """Step 2: 탭 전환 검증"""
        from PyQt6.QtTest import QTest
        from PyQt6.QtCore import Qt
        
        if not self.window or not hasattr(self.window, 'tabs'):
            result.add_check("사전 조건", False, "윈도우/탭 없음")
            return
            
        tab_count = cast(Any, self.window).tabs.count()
        self.log(f"총 {tab_count}개 탭 전환 테스트...")
        
        for i in range(tab_count):
            tab_name = cast(Any, self.window).tabs.tabText(i)
            self.log(f"  탭 {i}: {tab_name}")
            
            try:
                cast(Any, self.window).tabs.setCurrentIndex(i)
                cast(Any, QTest).qWait(500)
                
                # 현재 탭 확인
                current = cast(Any, self.window).tabs.currentIndex()
                switched = (current == i)
                
                # 현재 위젯 확인
                widget = cast(Any, self.window).tabs.currentWidget()
                checks, detail = self.check_widget(widget, f"Tab[{i}] Widget")
                
                result.add_check(f"탭 '{tab_name}' 전환", switched and all(checks.values()), 
                    detail if not all(checks.values()) else "")
                    
            except Exception as e:
                result.add_check(f"탭 '{tab_name}' 전환", False, str(e))
                
        self.capture_screenshot("step2_tabs")

    def test_optimization_data(self, result: StrictTestResult):
        """Step 3: 최적화 탭 데이터 로딩 검증"""
        from PyQt6.QtTest import QTest
        
        # 최적화 탭으로 이동
        for i in range(cast(Any, self.window).tabs.count()):
            if "최적화" in cast(Any, self.window).tabs.tabText(i):
                cast(Any, self.window).tabs.setCurrentIndex(i)
                break
        cast(Any, QTest).qWait(1000)
        
        page = cast(Any, self.window).optimization_widget
        if hasattr(page, 'single_widget'):
            page = page.single_widget
            
        # data_combo 검증
        if hasattr(page, 'data_combo'):
            result.add_check("data_combo 존재", True)
            
            # 데이터 로딩
            if hasattr(page, '_load_data_sources'):
                self.log("_load_data_sources() 호출...")
                page._load_data_sources()
                cast(Any, QTest).qWait(2000)
                
            count = page.data_combo.count()
            result.add_check("데이터 소스 로딩", count > 0, f"{count}개 항목")
            
            if count == 0:
                result.add_check("데이터 없음 = FAIL", False, "캐시 파일 없거나 로딩 실패")
        else:
            result.add_check("data_combo 존재", False, "속성 없음")
            
        self.capture_screenshot("step3_optimization")

    def test_backtest(self, result: StrictTestResult):
        """Step 4: 백테스트 탭 검증"""
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QPushButton
        
        # 백테스트 탭으로 이동
        for i in range(cast(Any, self.window).tabs.count()):
            if "백테스트" in cast(Any, self.window).tabs.tabText(i):
                cast(Any, self.window).tabs.setCurrentIndex(i)
                break
        cast(Any, QTest).qWait(1000)
        
        page = cast(Any, self.window).backtest_widget
        if hasattr(page, 'single_widget'):
            page = page.single_widget
            
        # 실행 버튼 찾기
        run_btn = None
        for btn in page.findChildren(QPushButton):
            if "백테스트" in btn.text() and "실행" in btn.text():
                run_btn = btn
                break
                
        if run_btn:
            result.add_check("실행 버튼 발견", True, run_btn.text())
            result.add_check("버튼 활성화", run_btn.isEnabled())
        else:
            result.add_check("실행 버튼 발견", False, "버튼 없음")
            
        self.capture_screenshot("step4_backtest")

    def run_all(self):
        """전체 테스트 실행"""
        print("\n" + "="*60)
        print("🔬 Strict GUI Test - 에러 감지 강화 버전")
        print("="*60)
        print(f"⏰ 시작: {datetime.now()}")
        
        # Step 1: Launch
        if not self.run_step("Step 1: GUI 실행", self.test_launch):
            print("\n⛔ Step 1 실패 - 테스트 중단")
            return self.generate_report()
            
        # Step 2: Tab Switch
        if not self.run_step("Step 2: 탭 전환", self.test_tab_switch):
            print("\n⛔ Step 2 실패 - 테스트 중단")
            return self.generate_report()
            
        # Step 3: Optimization
        if not self.run_step("Step 3: 최적화 데이터", self.test_optimization_data):
            print("\n⚠ Step 3 실패 - 계속 진행")
            
        # Step 4: Backtest
        if not self.run_step("Step 4: 백테스트", self.test_backtest):
            print("\n⚠ Step 4 실패 - 계속 진행")
            
        return self.generate_report()

    def generate_report(self):
        """결과 리포트 생성"""
        passed = sum(1 for r in self.results if r.passed)
        failed = len(self.results) - passed
        
        print("\n" + "="*60)
        print("📊 최종 결과")
        print("="*60)
        print(f"  총 테스트: {len(self.results)}")
        print(f"  ✅ 성공: {passed}")
        print(f"  ❌ 실패: {failed}")
        
        if failed > 0:
            print("\n❌ 실패한 테스트:")
            for r in self.results:
                if not r.passed:
                    print(f"  - {r.name}")
                    if r.error:
                        print(f"    Error: {r.error}")
                        
        # 리포트 파일 저장
        report_path = self.screenshot_dir / "gui_strict_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Strict GUI Test Report\n\n")
            f.write(f"- 테스트 시간: {datetime.now()}\n")
            f.write(f"- 총 테스트: {len(self.results)}\n")
            f.write(f"- 성공: {passed}\n")
            f.write(f"- 실패: {failed}\n\n")
            
            for r in self.results:
                f.write(f"## {r.name}\n")
                f.write(f"결과: {'PASS' if r.passed else 'FAIL'}\n\n")
                for c in r.checks:
                    status = "✅" if c["passed"] else "❌"
                    f.write(f"- {status} {c['name']}")
                    if c["detail"]:
                        f.write(f": {c['detail']}")
                    f.write("\n")
                if r.error:
                    f.write(f"\n**Error:** {r.error}\n")
                if r.traceback:
                    f.write(f"\n```\n{r.traceback}\n```\n")
                f.write("\n")
                
        print(f"\n📄 리포트 저장: {report_path}")
        
        return failed == 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", "-v", action="store_true", default=True)
    args = parser.parse_args()
    
    test = StrictGUITest(verbose=args.verbose)
    success = test.run_all()
    sys.exit(0 if success else 1)
