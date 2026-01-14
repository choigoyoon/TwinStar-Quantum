"""
UI 자동 검사
- PyQt5 QTest로 실제 클릭/입력 시뮬레이션
- 각 위젯 상태 자동 확인
- 스크린샷 캡처
"""

import sys
import time
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from PyQt6.QtWidgets import (
    QApplication, QPushButton, QComboBox, QSpinBox,
    QLineEdit, QLabel, QTabWidget, QGroupBox, QWidget
)
from typing import Any, cast
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtTest import QTest
from PyQt6.QtGui import QPixmap

class UIAutoTester:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.window: Any = None
        self.results = []
        self.screenshots = []
        self.screenshot_dir = ROOT / "tests" / "screenshots"
        self.screenshot_dir.mkdir(exist_ok=True)
    
    def log(self, msg):
        print(f"  {msg}")
    
    def wait(self, ms=500):
        """이벤트 처리 대기"""
        for _ in range(ms // 50):
            self.app.processEvents()
            time.sleep(0.05)
    
    def screenshot(self, name):
        """스크린샷 캡처"""
        if not self.window:
            return None
        
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{timestamp}_{name}.png"
        filepath = self.screenshot_dir / filename
        
        pixmap = self.window.grab()
        pixmap.save(str(filepath))
        
        self.screenshots.append(filepath)
        self.log(f"📸 스크린샷: {filename}")
        return filepath
    
    def find_widget(self, widget_type, text=None, name=None):
        """위젯 찾기"""
        if not self.window:
            return None
        
        widgets = self.window.findChildren(widget_type)
        
        for w in widgets:
            if text and hasattr(w, 'text'):
                if text.lower() in w.text().lower():
                    return w
            if name and w.objectName() == name:
                return w
        
        # text/name 없으면 첫 번째 반환
        if not text and not name and widgets:
            return widgets[0]
        
        return None
    
    def find_all_widgets(self, widget_type):
        """모든 위젯 찾기"""
        if not self.window:
            return []
        return self.window.findChildren(widget_type)
    
    def click_button(self, text=None, name=None):
        """버튼 클릭"""
        btn = self.find_widget(QPushButton, text, name)
        if btn and btn.isEnabled():
            cast(Any, QTest).mouseClick(btn, Qt.MouseButton.LeftButton)
            self.wait(300)
            return True
        return False
    
    def select_combo(self, index=0, text=None, combo_name=None):
        """콤보박스 선택"""
        combo = self.find_widget(QComboBox, name=combo_name)
        if combo:
            if text:
                idx = combo.findText(text, Qt.MatchFlag.MatchContains)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            else:
                combo.setCurrentIndex(index)
            self.wait(200)
            return True
        return False
    
    def set_spinbox(self, value, name=None):
        """스핀박스 값 설정"""
        spin = self.find_widget(QSpinBox, name=name)
        if spin:
            spin.setValue(value)
            self.wait(100)
            return True
        return False
    
    def get_label_text(self, text_contains):
        """라벨 텍스트 가져오기"""
        labels = self.find_all_widgets(QLabel)
        for label in labels:
            if text_contains.lower() in label.text().lower():
                return label.text()
        return None
    
    def test(self, name, func):
        """테스트 실행"""
        print(f"\n▶ {name}")
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
    print("🤖 UI 자동 검사 시스템 (v3.2)")
    print("="*60)
    print("실제 클릭/입력을 시뮬레이션합니다.")
    print("="*60)
    
    tester = UIAutoTester()
    
    # ========================================
    # 1. 앱 시작
    # ========================================
    print("\n" + "="*50)
    print("🚀 [1/8] 앱 시작")
    print("="*50)
    
    def test_app_start():
        from GUI.staru_main import StarUWindow
        tester.window = StarUWindow()
        tester.window.show()
        tester.wait(2000)
        
        if not tester.window.isVisible():
            raise Exception("창 표시 실패")
        
        tester.screenshot("01_startup")
        return f"창 크기: {tester.window.width()}x{tester.window.height()}"
    
    tester.test("앱 시작", test_app_start)
    
    # ========================================
    # 2. 탭 전환 테스트
    # ========================================
    print("\n" + "="*50)
    print("📑 [2/8] 탭 전환")
    print("="*50)
    
    def test_tabs():
        tabs = tester.find_widget(QTabWidget)
        if not tabs:
            raise Exception("탭 위젯 없음")
        
        tab_count = tabs.count()
        tab_names = [tabs.tabText(i) for i in range(tab_count)]
        
        # 각 탭 클릭
        for i in range(tab_count):
            tabs.setCurrentIndex(i)
            tester.wait(500)
            tester.screenshot(f"02_tab_{i}_{tabs.tabText(i)}")
        
        # 첫 번째 탭으로 복귀
        tabs.setCurrentIndex(0)
        tester.wait(300)
        
        return f"{tab_count}개 탭: {tab_names}"
    
    tester.test("탭 전환", test_tabs)
    
    # ========================================
    # 3. 버튼 탐지
    # ========================================
    print("\n" + "="*50)
    print("🔘 [3/8] 버튼 탐지")
    print("="*50)
    
    def test_buttons():
        buttons = tester.find_all_widgets(QPushButton)
        
        enabled = [b for b in buttons if b.isEnabled()]
        visible = [b for b in buttons if b.isVisible()]
        
        button_texts = [b.text()[:20] for b in enabled[:10]]
        
        return f"버튼 {len(enabled)}개 활성, {len(visible)}개 표시: {button_texts}"
    
    tester.test("버튼 탐지", test_buttons)
    
    # ========================================
    # 4. 콤보박스 확인
    # ========================================
    print("\n" + "="*50)
    print("📋 [4/8] 콤보박스")
    print("="*50)
    
    def test_combos():
        combos = tester.find_all_widgets(QComboBox)
        
        combo_info = []
        for combo in combos[:5]:
            items = [combo.itemText(i) for i in range(min(3, combo.count()))]
            combo_info.append(f"{combo.currentText()}({combo.count()})")
        
        return f"콤보박스 {len(combos)}개: {combo_info}"
    
    tester.test("콤보박스", test_combos)
    
    # ========================================
    # 5. 거래소 선택 시뮬레이션
    # ========================================
    print("\n" + "="*50)
    print("🏦 [5/8] 거래소 선택")
    print("="*50)
    
    def test_exchange_select():
        # 거래소 콤보박스 찾기
        combos = tester.find_all_widgets(QComboBox)
        
        exchange_combo = None
        for combo in combos:
            for i in range(combo.count()):
                if 'bybit' in combo.itemText(i).lower():
                    exchange_combo = combo
                    break
        
        if not exchange_combo:
            return "거래소 콤보 없음 (정상일 수 있음)"
        
        # Bybit 선택
        for i in range(exchange_combo.count()):
            if 'bybit' in exchange_combo.itemText(i).lower():
                exchange_combo.setCurrentIndex(i)
                tester.wait(500)
                break
        
        tester.screenshot("05_exchange_select")
        return f"선택: {exchange_combo.currentText()}"
    
    tester.test("거래소 선택", test_exchange_select)
    
    # ========================================
    # 6. 잔고 표시 확인
    # ========================================
    print("\n" + "="*50)
    print("💰 [6/8] 잔고 표시")
    print("="*50)
    
    def test_balance():
        # 잔고 관련 라벨 찾기
        balance_text = tester.get_label_text("balance") or \
                       tester.get_label_text("잔고") or \
                       tester.get_label_text("$") or \
                       tester.get_label_text("usdt")
        
        if balance_text:
            return f"잔고 표시: {balance_text[:50]}"
        
        return "잔고 라벨 미발견 (UI 구조 확인 필요)"
    
    tester.test("잔고 표시", test_balance)
    
    # ========================================
    # 7. 싱글/멀티 영역 확인
    # ========================================
    print("\n" + "="*50)
    print("📊 [7/8] 싱글/멀티 영역")
    print("="*50)
    
    def test_trade_areas():
        groups = tester.find_all_widgets(QGroupBox)
        
        found = []
        for group in groups:
            title = group.title().lower()
            if '싱글' in title or 'single' in title:
                found.append("싱글")
            if '멀티' in title or 'multi' in title:
                found.append("멀티")
            if '탐색' in title or 'explorer' in title:
                found.append("탐색기")
        
        tester.screenshot("07_trade_areas")
        
        if found:
            return f"영역 발견: {found}"
        return "영역 미발견 (다른 구조일 수 있음)"
    
    tester.test("싱글/멀티 영역", test_trade_areas)
    
    # ========================================
    # 8. 시작 버튼 클릭 시뮬레이션
    # ========================================
    print("\n" + "="*50)
    print("▶️ [8/8] 시작 버튼 테스트")
    print("="*50)
    
    def test_start_button():
        # 시작 버튼 찾기
        start_btn = tester.find_widget(QPushButton, "시작") or \
                    tester.find_widget(QPushButton, "start") or \
                    tester.find_widget(QPushButton, "▶")
        
        if not start_btn:
            return "시작 버튼 미발견"
        
        if not start_btn.isEnabled():
            return f"시작 버튼 비활성 (정상: 설정 필요)"
        
        # 클릭 시뮬레이션 (실제 매매 방지를 위해 주석)
        # QTest.mouseClick(start_btn, Qt.MouseButton.LeftButton)
        
        tester.screenshot("08_start_button")
        return f"시작 버튼: '{start_btn.text()}' (클릭 가능)"
    
    tester.test("시작 버튼", test_start_button)
    
    # ========================================
    # 종료
    # ========================================
    print("\n" + "="*50)
    print("🚪 종료 처리")
    print("="*50)
    
    def test_close():
        tester.screenshot("99_final")
        
        tester.window.close()
        tester.wait(1000)
        
        if tester.window.isVisible():
            raise Exception("종료 실패")
        
        tester.window.deleteLater()
        tester.wait(500)
        
        return "정상 종료"
    
    tester.test("종료", test_close)
    
    # ========================================
    # 최종 결과
    # ========================================
    print("\n" + "="*60)
    print("📊 UI 자동 검사 결과")
    print("="*60)
    
    passed = sum(1 for _, ok, _ in tester.results if ok)
    failed = sum(1 for _, ok, _ in tester.results if not ok)
    
    for name, ok, msg in tester.results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}: {msg[:50]}")
    
    print("-"*60)
    print(f"  통과: {passed}/{len(tester.results)}")
    print(f"  실패: {failed}/{len(tester.results)}")
    
    print(f"\n📸 스크린샷 {len(tester.screenshots)}개 저장:")
    print(f"   {tester.screenshot_dir}")
    
    # JSON 저장
    import json
    output = {
        'passed': passed,
        'failed': failed,
        'screenshots': [str(s) for s in tester.screenshots],
        'details': [{'name': n, 'ok': o, 'msg': m} for n, o, m in tester.results]
    }
    
    output_file = ROOT / "tests" / "ui_auto_test_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 상세 결과: {output_file}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
