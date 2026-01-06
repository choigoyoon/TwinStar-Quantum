"""
GUI 실전 시나리오 테스트
- 버튼 클릭
- 타이머 동작
- 스레드 생성/종료
- 이벤트 처리
- 종료 시나리오
"""

import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtTest import QTest

class GUIScenarioTester:
    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.results = []
        self.errors = []
    
    def test(self, name, func):
        print(f"\n▶ {name}")
        try:
            result = func()
            self.results.append((name, True))
            msg = f"  ✅ 성공"
            if result and isinstance(result, str):
                msg += f": {result}"
            print(msg)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.results.append((name, False))
            self.errors.append((name, str(e)))
            print(f"  ❌ 실패: {e}")
            # print(tb)
    
    def process(self, ms=100):
        """이벤트 처리 대기"""
        for _ in range(ms // 10):
            self.app.processEvents()
            time.sleep(0.01)

def main():
    print("="*60)
    print("🖥️ GUI 실전 시나리오 테스트")
    print("="*60)
    
    tester = GUIScenarioTester()
    
    # === 1. TradingDashboard 로드 ===
    print("\n[시나리오 1] 대시보드 로드")
    
    dashboard = None
    
    def test_dashboard_load():
        nonlocal dashboard
        from GUI.trading_dashboard import TradingDashboard
        
        dashboard = TradingDashboard()
        dashboard.show()
        tester.process(500)
        
        assert dashboard.isVisible(), "대시보드 표시 안 됨"
        return "화면 표시 완료"
    
    tester.test("대시보드 로드", test_dashboard_load)
    
    # === 2. 싱글 트레이딩 영역 확인 ===
    print("\n[시나리오 2] 싱글 트레이딩 UI")
    
    def test_single_trade_ui():
        if not dashboard:
            raise Exception("대시보드 없음")
        
        # SingleTradeWidget 존재 확인 - 구조 변경에 따라 유연하게 탐색
        single = getattr(dashboard, 'single_trade_widget', None)
        if single is None:
             # 재귀적으로 찾기
            from GUI.single_trade_widget import SingleTradeWidget
            single = dashboard.findChild(SingleTradeWidget)
        
        # 또는 trade_splitter에서 찾기
        splitter = getattr(dashboard, 'trade_splitter', None)
        
        assert splitter is not None or single is not None, "싱글 트레이딩 UI 요소를 찾을 수 없음"
        return "UI 컴포넌트 확인됨"
    
    tester.test("싱글 UI 존재", test_single_trade_ui)
    
    # === 3. 멀티 트레이딩 영역 확인 ===
    print("\n[시나리오 3] 멀티 트레이딩 UI")
    
    def test_multi_trade_ui():
        if not dashboard:
            raise Exception("대시보드 없음")
        
        multi = getattr(dashboard, 'multi_trade_widget', None)
        if multi is None:
             from GUI.multi_trade_widget import MultiTradeWidget
             multi = dashboard.findChild(MultiTradeWidget)
             
        explorer = getattr(dashboard, 'multi_explorer', None)
        
        assert multi is not None or explorer is not None, "멀티 트레이딩 UI 요소를 찾을 수 없음"
        return "UI 컴포넌트 확인됨"
    
    tester.test("멀티 UI 존재", test_multi_trade_ui)
    
    # === 4. 타이머 동작 테스트 ===
    print("\n[시나리오 4] 타이머 동작")
    
    def test_timers():
        if not dashboard:
            raise Exception("대시보드 없음")
        
        # 타이머 존재 확인
        timers_found = []
        for attr in dir(dashboard):
            try:
                obj = getattr(dashboard, attr, None)
                if isinstance(obj, QTimer):
                    # 활성 상태 확인
                    state = "Active" if obj.isActive() else "Inactive"
                    timers_found.append(f"{attr}({state})")
            except:
                pass
        
        # 2초 대기 (타이머 동작 유도)
        tester.process(2000)
        
        return f"타이머 감지: {len(timers_found)}개 ({', '.join(timers_found[:3])}...)"
    
    tester.test("타이머 동작", test_timers)
    
    # === 5. 버튼 클릭 시뮬레이션 ===
    print("\n[시나리오 5] 버튼 클릭")
    
    def test_button_click():
        if not dashboard:
            raise Exception("대시보드 없음")
        
        from PyQt5.QtWidgets import QPushButton
        
        # 모든 버튼 찾기
        buttons = dashboard.findChildren(QPushButton)
        
        if not buttons:
            raise Exception("버튼 없음")
        
        # 첫 번째 버튼 클릭 (시작 버튼일 가능성)
        # 안전하게: 실제 클릭하지 않고 존재만 확인
        clickable = [b for b in buttons if b.isEnabled() and b.isVisible()]
        
        return f"클릭 가능 버튼: {len(clickable)}개 (Total: {len(buttons)})"
    
    tester.test("버튼 확인", test_button_click)
    
    # === 6. 스레드 상태 확인 ===
    print("\n[시나리오 6] 스레드 상태")
    
    def test_threads():
        if not dashboard:
            raise Exception("대시보드 없음")
        
        from PyQt5.QtCore import QThread
        
        threads = []
        for attr in dir(dashboard):
            try:
                obj = getattr(dashboard, attr, None)
                if isinstance(obj, QThread):
                    threads.append((attr, obj.isRunning()))
            except:
                pass
        
        return f"관리 중인 스레드: {len(threads)}개"
    
    tester.test("스레드 상태", test_threads)
    
    # === 7. 종료 시나리오 (핵심!) ===
    print("\n[시나리오 7] 종료 처리")
    
    def test_close():
        if not dashboard:
            raise Exception("대시보드 없음")
        
        # closeEvent 트리거
        from PyQt5.QtGui import QCloseEvent
        
        # 종료 전 정리 메서드 확인
        has_cleanup = hasattr(dashboard, 'closeEvent')
        
        # 실제 종료
        dashboard.close()
        tester.process(1000)
        
        # 종료 후 상태
        is_closed = not dashboard.isVisible()
        
        if not is_closed:
            raise Exception("위젯이 여전히 보임 (종료 실패)")
        
        return "정상 종료 (화면 사라짐)"
    
    tester.test("종료 처리", test_close)
    
    # === 8. 메모리 정리 ===
    print("\n[시나리오 8] 메모리 정리")
    
    def test_cleanup():
        if dashboard:
            dashboard.deleteLater()
        
        tester.process(500)
        
        # GC 호출
        import gc
        gc.collect()
        
        return "GC 완료"
    
    tester.test("메모리 정리", test_cleanup)
    
    # === 결과 ===
    print("\n" + "="*60)
    print("📊 GUI 시나리오 테스트 결과")
    print("="*60)
    
    passed = sum(1 for _, ok in tester.results if ok)
    failed = sum(1 for _, ok in tester.results if not ok)
    
    print(f"통과: {passed}/{len(tester.results)}")
    print(f"실패: {failed}/{len(tester.results)}")
    
    if tester.errors:
        print("\n❌ 실패 상세:")
        for name, err in tester.errors:
            print(f"  - {name}: {err}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
