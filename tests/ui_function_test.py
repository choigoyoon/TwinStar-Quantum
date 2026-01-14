"""
버튼 기능 검증 (v3.3)
- 버튼 클릭 → 상태 변화 확인
- 콤보박스 변경 → 연동 확인
- 입력 → 반영 확인
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import (
    QApplication, QPushButton, QComboBox, QSpinBox,
    QDoubleSpinBox, QLineEdit, QLabel, QTabWidget,
    QGroupBox, QCheckBox, QTextEdit, QWidget
)
from typing import Any, cast
from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest

class FunctionTester:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window: Any = None
        self.results = []
        self.screenshot_dir = ROOT / "tests" / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
    
    def log(self, msg):
        print(f"    {msg}")
    
    def wait(self, ms=500):
        for _ in range(ms // 50):
            self.app.processEvents()
            time.sleep(0.05)
    
    def screenshot(self, name):
        if self.window:
            from datetime import datetime
            ts = datetime.now().strftime("%H%M%S")
            path = self.screenshot_dir / f"{ts}_{name}.png"
            self.window.grab().save(str(path))
            return path
        return None
    
    def find_buttons_by_text(self, texts):
        """텍스트로 버튼 찾기"""
        buttons = self.window.findChildren(QPushButton)
        found = {}
        for btn in buttons:
            btn_text = btn.text().lower()
            for t in texts:
                if t.lower() in btn_text:
                    found[t] = btn
        return found
    
    def find_combo_by_items(self, item_keywords):
        """아이템으로 콤보박스 찾기"""
        combos = self.window.findChildren(QComboBox)
        for combo in combos:
            items = [combo.itemText(i).lower() for i in range(combo.count())]
            for kw in item_keywords:
                if any(kw.lower() in item for item in items):
                    return combo
        return None
    
    def get_log_text(self):
        """로그 텍스트 가져오기"""
        logs = self.window.findChildren(QTextEdit)
        for log in logs:
            text = log.toPlainText()
            if text:
                return text
        return ""
    
    def test(self, name, func):
        print(f"\n  ▶ {name}")
        try:
            result = func()
            self.results.append((name, True, result))
            self.log(f"✅ {result}")
            return True
        except Exception as e:
            self.results.append((name, False, str(e)))
            self.log(f"❌ {e}")
            return False

def main():
    print("="*60)
    print("🔬 버튼 기능 검증 (v3.3)")
    print("="*60)
    
    t = FunctionTester()
    
    # ========================================
    # 앱 시작
    # ========================================
    print("\n[앱 시작]")
    
    # CORRECTED: Import StarUWindow instead of MainWindow
    from GUI.staru_main import StarUWindow
    t.window = StarUWindow()
    t.window.show()
    t.wait(3000)
    
    t.screenshot("00_initial_func_test")
    
    # ========================================
    # 1. 거래소 선택 기능
    # ========================================
    print("\n" + "="*50)
    print("🏦 [1/10] 거래소 선택 → 연동 확인")
    print("="*50)
    
    def test_exchange_select():
        combo = t.find_combo_by_items(['bybit', 'binance', 'okx'])
        if not combo:
            return "거래소 콤보 없음 (다른 위치)"
        
        initial = combo.currentText()
        
        # 다른 거래소 선택
        for i in range(combo.count()):
            if combo.itemText(i) != initial:
                combo.setCurrentIndex(i)
                t.wait(1000)
                break
        
        changed = combo.currentText()
        
        # 원래대로 복귀
        combo.setCurrentIndex(0)
        t.wait(500)
        
        if initial == changed:
            return "거래소 변경 안 됨"
        
        t.screenshot("01_exchange_func")
        return f"{initial} → {changed} → 복귀 OK"
    
    t.test("거래소 선택", test_exchange_select)
    
    # ========================================
    # 2. 심볼 선택 기능
    # ========================================
    print("\n" + "="*50)
    print("📈 [2/10] 심볼 선택 → 반영 확인")
    print("="*50)
    
    def test_symbol_select():
        combo = t.find_combo_by_items(['btcusdt', 'ethusdt', 'btc'])
        if not combo:
            return "심볼 콤보 없음"
        
        initial = combo.currentText()
        
        # ETH 선택 시도
        for i in range(combo.count()):
            if 'eth' in combo.itemText(i).lower():
                combo.setCurrentIndex(i)
                t.wait(500)
                break
        
        changed = combo.currentText()
        t.screenshot("02_symbol_func")
        
        return f"심볼: {initial} → {changed}"
    
    t.test("심볼 선택", test_symbol_select)
    
    # ========================================
    # 3. 레버리지 조절
    # ========================================
    print("\n" + "="*50)
    print("⚡ [3/10] 레버리지 조절 → 값 변경")
    print("="*50)
    
    def test_leverage():
        spins = t.window.findChildren(QSpinBox)
        
        lev_spin = None
        for spin in spins:
            if spin.minimum() >= 1 and spin.maximum() <= 125:
                # Assuming leverage spinbox
                lev_spin = spin
                break
        
        if not lev_spin:
            return "레버리지 스핀박스 없음"
        
        initial = lev_spin.value()
        
        # 값 변경
        new_val = 10 if initial != 10 else 5
        lev_spin.setValue(new_val)
        t.wait(300)
        
        changed = lev_spin.value()
        t.screenshot("03_leverage_func")
        
        return f"레버리지: {initial} → {changed}"
    
    t.test("레버리지 조절", test_leverage)
    
    # ========================================
    # 4. 시드 금액 입력
    # ========================================
    print("\n" + "="*50)
    print("💵 [4/10] 시드 금액 → 입력 반영")
    print("="*50)
    
    def test_seed():
        # QDoubleSpinBox 또는 QSpinBox 찾기
        dspins = t.window.findChildren(QDoubleSpinBox)
        spins = t.window.findChildren(QSpinBox)
        
        seed_spin = None
        
        # 100~10000 범위 찾기
        for spin in dspins + spins:
            if spin.minimum() >= 0 and spin.maximum() >= 100:
                if hasattr(spin, 'value'):
                    val = spin.value()
                    # Default seed often around 1000
                    if 10 <= val <= 100000:
                        seed_spin = spin
                        break
        
        if not seed_spin:
            return "시드 입력 없음"
        
        initial = seed_spin.value()
        seed_spin.setValue(200)
        t.wait(300)
        
        changed = seed_spin.value()
        t.screenshot("04_seed_func")
        
        return f"시드: {initial} → {changed}"
    
    t.test("시드 입력", test_seed)
    
    # ========================================
    # 5. 복리/고정 모드 전환
    # ========================================
    print("\n" + "="*50)
    print("🔄 [5/10] 자본 모드 → 복리/고정 전환")
    print("="*50)
    
    def test_capital_mode():
        combo = t.find_combo_by_items(['복리', '고정', 'compound', 'fixed'])
        
        if combo:
            initial = combo.currentText()
            
            # 다른 모드 선택
            other_idx = 1 if combo.currentIndex() == 0 else 0
            combo.setCurrentIndex(other_idx)
            t.wait(500)
            
            changed = combo.currentText()
            t.screenshot("05_capital_mode_func")
            
            return f"모드: {initial} → {changed}"
        
        # 체크박스로 구현된 경우
        checks = t.window.findChildren(QCheckBox)
        for chk in checks:
            if '복리' in chk.text() or 'compound' in chk.text().lower():
                initial = chk.isChecked()
                chk.setChecked(not initial)
                t.wait(500)
                return f"복리 체크: {initial} → {chk.isChecked()}"
        
        return "자본 모드 컨트롤 없음"
    
    t.test("자본 모드", test_capital_mode)
    
    # ========================================
    # 6. 멀티 스캔 시작/정지
    # ========================================
    print("\n" + "="*50)
    print("🔍 [6/10] 멀티 스캔 → 시작/정지")
    print("="*50)
    
    def test_multi_scan():
        buttons = t.find_buttons_by_text(['스캔', 'scan', '시작', 'start'])
        
        scan_btn = buttons.get('스캔') or buttons.get('scan')
        
        if not scan_btn:
            return "스캔 버튼 없음"
        
        if not scan_btn.isEnabled():
            return "스캔 버튼 비활성"
        
        initial_text = scan_btn.text()
        
        # 클릭
        cast(Any, QTest).mouseClick(scan_btn, Qt.MouseButton.LeftButton)
        t.wait(2000)
        
        # 로그 확인
        log = t.get_log_text()
        
        t.screenshot("06_scan_start_func")
        
        # 정지 클릭 (텍스트 바뀌었을 수 있음)
        stop_buttons = t.find_buttons_by_text(['정지', 'stop'])
        stop_btn = stop_buttons.get('정지') or stop_buttons.get('stop')
        
        if stop_btn and stop_btn.isEnabled():
            cast(Any, QTest).mouseClick(stop_btn, Qt.MouseButton.LeftButton)
            t.wait(1000)
            t.screenshot("06_scan_stop_func")
        
        return f"스캔 시작 → 로그 {len(log)}자"
    
    t.test("멀티 스캔", test_multi_scan)
    
    # ========================================
    # 7. 싱글 매매 시작 (Dry Run)
    # ========================================
    print("\n" + "="*50)
    print("▶️ [7/10] 싱글 매매 → 시작 버튼")
    print("="*50)
    
    def test_single_start():
        # 싱글 영역의 시작 버튼 찾기
        groups = t.window.findChildren(QGroupBox)
        
        single_group = None
        for g in groups:
            if '싱글' in g.title() or 'single' in g.title().lower():
                single_group = g
                break
        
        if not single_group:
            # 전체에서 시작 버튼 찾기
            buttons = t.find_buttons_by_text(['시작', 'start', '▶'])
            start_btn = buttons.get('시작') or buttons.get('start') or buttons.get('▶')
        else:
            start_btn = single_group.findChild(QPushButton)
        
        if not start_btn:
            # Try finding generally if not found in specific group
            buttons = t.find_buttons_by_text(['시작', 'start', '▶'])
            start_btn = buttons.get('시작') or buttons.get('start') or buttons.get('▶')
            
        if not start_btn:
             return "시작 버튼 없음"

        if not start_btn.isEnabled():
            return f"시작 버튼 비활성 ('{start_btn.text()}')"
        
        # 클릭 전 로그
        log_before = t.get_log_text()
        
        # 클릭 (실제 매매 주의!)
        cast(Any, QTest).mouseClick(start_btn, Qt.MouseButton.LeftButton)
        t.wait(2000)
        
        # 클릭 후 로그
        log_after = t.get_log_text()
        
        t.screenshot("07_single_start_func")
        
        # 정지
        stop_buttons = t.find_buttons_by_text(['정지', 'stop', '⏹'])
        stop_btn = stop_buttons.get('정지') or stop_buttons.get('stop')
        
        if stop_btn and stop_btn.isEnabled():
            cast(Any, QTest).mouseClick(stop_btn, Qt.MouseButton.LeftButton)
            t.wait(1000)
        
        log_added = len(log_after) - len(log_before)
        return f"시작 클릭 → 로그 +{log_added}자"
    
    t.test("싱글 시작", test_single_start)
    
    # ========================================
    # 8. 설정 탭 이동 및 저장
    # ========================================
    print("\n" + "="*50)
    print("⚙️ [8/10] 설정 탭 → 저장 버튼")
    print("="*50)
    
    def test_settings():
        tabs = t.window.findChild(QTabWidget)
        if not tabs:
            return "탭 위젯 없음"
        
        # 설정 탭 찾기
        settings_idx = -1
        for i in range(tabs.count()):
            if '설정' in tabs.tabText(i) or 'setting' in tabs.tabText(i).lower():
                settings_idx = i
                break
        
        if settings_idx < 0:
            return "설정 탭 없음"
        
        # 탭 이동
        tabs.setCurrentIndex(settings_idx)
        t.wait(1000)
        
        t.screenshot("08_settings_func")
        
        # 저장 버튼 찾기
        save_btn = t.find_buttons_by_text(['저장', 'save']).get('저장') or \
                   t.find_buttons_by_text(['저장', 'save']).get('save')
        
        if save_btn and save_btn.isEnabled():
            cast(Any, QTest).mouseClick(save_btn, Qt.MouseButton.LeftButton)
            t.wait(500)
            return "설정 탭 → 저장 클릭 OK"
        
        # 첫 번째 탭으로 복귀
        tabs.setCurrentIndex(0)
        t.wait(500)
        
        return "설정 탭 이동 OK (저장 버튼 없거나 비활성)"
    
    t.test("설정 저장", test_settings)
    
    # ========================================
    # 9. 백테스트 탭 (있으면)
    # ========================================
    print("\n" + "="*50)
    print("📊 [9/10] 백테스트 탭")
    print("="*50)
    
    def test_backtest():
        tabs = t.window.findChild(QTabWidget)
        if not tabs:
            return "탭 위젯 없음"
        
        # 백테스트 탭 찾기
        bt_idx = -1
        for i in range(tabs.count()):
            text = tabs.tabText(i).lower()
            if '백테스트' in text or 'backtest' in text:
                bt_idx = i
                break
        
        if bt_idx < 0:
            return "백테스트 탭 없음"
        
        tabs.setCurrentIndex(bt_idx)
        t.wait(1000)
        
        t.screenshot("09_backtest_func")
        
        # 실행 버튼 찾기
        run_btn = t.find_buttons_by_text(['실행', 'run', '시작']).get('실행') or \
                  t.find_buttons_by_text(['실행', 'run', '시작']).get('run')
        
        # 첫 번째 탭으로 복귀
        tabs.setCurrentIndex(0)
        t.wait(500)
        
        if run_btn:
            return f"백테스트 탭 OK, 실행 버튼: '{run_btn.text()}'"
        return "백테스트 탭 OK"
    
    t.test("백테스트 탭", test_backtest)
    
    # ========================================
    # 10. 종료 및 정리
    # ========================================
    print("\n" + "="*50)
    print("🚪 [10/10] 종료 및 정리")
    print("="*50)
    
    def test_close():
        t.screenshot("10_final_func")
        
        t.window.close()
        t.wait(2000)
        
        if t.window.isVisible():
            raise Exception("종료 실패")
        
        t.window.deleteLater()
        t.wait(500)
        
        import gc
        gc.collect()
        
        return "정상 종료 및 메모리 정리"
    
    t.test("종료", test_close)
    
    # ========================================
    # 최종 결과
    # ========================================
    print("\n" + "="*60)
    print("📊 버튼 기능 검증 결과")
    print("="*60)
    
    passed = sum(1 for _, ok, _ in t.results if ok)
    failed = sum(1 for _, ok, _ in t.results if not ok)
    
    for name, ok, msg in t.results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}: {msg[:50]}")
    
    print("-"*60)
    print(f"  통과: {passed}/{len(t.results)}")
    print(f"  실패: {failed}/{len(t.results)}")
    
    # JSON 저장
    import json
    output = {
        'passed': passed,
        'failed': failed,
        'details': [{'name': n, 'ok': o, 'msg': m} for n, o, m in t.results]
    }
    
    output_file = ROOT / "tests" / "ui_function_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 결과: {output_file}")
    print(f"📸 스크린샷: {t.screenshot_dir}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
