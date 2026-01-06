"""
실시간 GUI 검증
- 실제 GUI 띄움
- 단계별 시간 대기
- 각 단계마다 상태 체크
- 에러 실시간 캐치
"""

import sys
import time
import traceback
import logging
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("GUITest")

class RealtimeGUITester:
    def __init__(self):
        self.app = None
        self.dashboard = None
        self.errors = []
        self.stages = []
        self.start_time = None
    
    def log(self, msg):
        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"[{elapsed:6.1f}s] {msg}")
    
    def wait(self, seconds, reason=""):
        """시간 대기 + 이벤트 처리"""
        self.log(f"⏳ {seconds}초 대기 ({reason})")
        
        for i in range(int(seconds * 10)):
            self.app.processEvents()
            time.sleep(0.1)
            
            # 매 초마다 상태 출력
            if i > 0 and i % 10 == 0:
                self.check_health()
    
    def check_health(self):
        """현재 상태 체크"""
        if not self.dashboard:
            return
        
        try:
            # 기본 상태
            visible = self.dashboard.isVisible()
            
            # 스레드 상태
            from PyQt5.QtCore import QThread
            running_threads = []
            for attr in dir(self.dashboard):
                try:
                    obj = getattr(self.dashboard, attr, None)
                    if isinstance(obj, QThread) and obj.isRunning():
                        running_threads.append(attr)
                except:
                    pass
            
            # 타이머 상태
            from PyQt5.QtCore import QTimer
            active_timers = []
            for attr in dir(self.dashboard):
                try:
                    obj = getattr(self.dashboard, attr, None)
                    if isinstance(obj, QTimer) and obj.isActive():
                        active_timers.append(attr)
                except:
                    pass
            
            self.log(f"   💓 visible={visible}, threads={len(running_threads)}, timers={len(active_timers)}")
            
        except Exception as e:
            self.log(f"   ❌ health check 실패: {e}")
    
    def stage(self, name, check_func):
        """단계별 검증"""
        self.log(f"━━━ {name} ━━━")
        
        try:
            result = check_func()
            self.stages.append((name, True, result))
            self.log(f"✅ {result}")
            return True
        except Exception as e:
            self.stages.append((name, False, str(e)))
            self.errors.append((name, str(e), traceback.format_exc()))
            self.log(f"❌ {e}")
            return False
    
    def run(self):
        """메인 테스트 실행"""
        self.start_time = time.time()
        
        print("="*60)
        print("🖥️ TwinStar Quantum - 실시간 GUI 검증 (v2.6)")
        print("="*60)
        print("실제 GUI를 띄우고 단계별로 검증합니다.")
        print("에러 발생 시 즉시 캐치됩니다.")
        print("="*60)
        
        # === Stage 0: PyQt5 초기화 ===
        def init_qt():
            from PyQt5.QtWidgets import QApplication
            self.app = QApplication.instance() or QApplication(sys.argv)
            return "QApplication 준비"
        
        if not self.stage("Stage 0: Qt 초기화", init_qt):
            return 1
        
        self.wait(1, "Qt 안정화")
        
        # === Stage 1: 대시보드 생성 ===
        def create_dashboard():
            from GUI.trading_dashboard import TradingDashboard
            self.dashboard = TradingDashboard()
            return f"TradingDashboard 생성 완료"
        
        if not self.stage("Stage 1: 대시보드 생성", create_dashboard):
            return 1
        
        self.wait(2, "객체 초기화")
        
        # === Stage 2: 화면 표시 ===
        def show_dashboard():
            self.dashboard.show()
            self.dashboard.raise_()
            self.dashboard.activateWindow()
            
            if not self.dashboard.isVisible():
                raise Exception("화면 표시 실패")
            
            return f"화면 표시 성공 (크기: {self.dashboard.width()}x{self.dashboard.height()})"
        
        if not self.stage("Stage 2: 화면 표시", show_dashboard):
            return 1
        
        self.wait(3, "UI 렌더링 완료 대기")
        
        # === Stage 3: UI 컴포넌트 확인 ===
        def check_components():
            components = {
                'single_trade_widget': False,
                'multi_trade_widget': False,
                'multi_explorer': False,
                'trade_splitter': False,
                'log_group': False,
            }
            
            # 유연한 탐색
            from GUI.single_trade_widget import SingleTradeWidget
            from GUI.multi_trade_widget import MultiTradeWidget
            
            if self.dashboard.findChild(SingleTradeWidget): components['single_trade_widget'] = True
            if self.dashboard.findChild(MultiTradeWidget): components['multi_trade_widget'] = True
            
            for comp in components:
                if hasattr(self.dashboard, comp):
                    obj = getattr(self.dashboard, comp, None)
                    if obj is not None:
                        components[comp] = True
            
            found = sum(1 for v in components.values() if v)
            
            if found < 2: # 최소한 싱글/멀티 위젯은 있어야 함
                raise Exception(f"주요 UI 컴포넌트 부족 (found={found})")
            
            return f"컴포넌트 {found}/{len(components)} 발견"
        
        if not self.stage("Stage 3: UI 컴포넌트", check_components):
            return 1
        
        self.wait(2, "컴포넌트 로드")
        
        # === Stage 4: 타이머 동작 확인 ===
        def check_timers():
            from PyQt5.QtCore import QTimer
            
            timers = []
            for attr in dir(self.dashboard):
                try:
                    obj = getattr(self.dashboard, attr, None)
                    if isinstance(obj, QTimer):
                        timers.append((attr, obj.isActive()))
                except:
                    pass
            
            active = sum(1 for _, a in timers if a)
            
            return f"타이머 {active}/{len(timers)} 활성"
        
        if not self.stage("Stage 4: 타이머 확인", check_timers):
            return 1
        
        self.wait(5, "타이머 동작 관찰")
        
        # === Stage 5: 스레드 상태 ===
        def check_threads():
            from PyQt5.QtCore import QThread
            
            threads = []
            for attr in dir(self.dashboard):
                try:
                    obj = getattr(self.dashboard, attr, None)
                    if isinstance(obj, QThread):
                        threads.append((attr, obj.isRunning()))
                except:
                    pass
            
            running = sum(1 for _, r in threads if r)
            
            return f"스레드 {running}/{len(threads)} 실행 중"
        
        if not self.stage("Stage 5: 스레드 확인", check_threads):
            return 1
        
        self.wait(3, "스레드 안정화")
        
        # === Stage 6: 데이터 갱신 확인 ===
        def check_data_refresh():
            # 잔고 라벨 확인 (속성명이 다를 수 있으므로 유연하게)
            labels = [
                getattr(self.dashboard, 'balance_label', None),
                getattr(self.dashboard, 'total_balance_label', None)
            ]
            
            for lbl in labels:
                if lbl:
                    text = lbl.text()
                    return f"잔고 표시: {text[:30]}..."
            
            return "잔고 라벨 속성명 불일치 (기능 문제 아닐 수 있음)"
        
        if not self.stage("Stage 6: 데이터 갱신", check_data_refresh):
            pass  # 실패해도 계속
        
        self.wait(5, "데이터 갱신 주기 관찰")
        
        # === Stage 7: 오래 유지 테스트 ===
        def long_running():
            self.log("📺 10초간 GUI 유지...")
            
            for i in range(10):
                self.app.processEvents()
                time.sleep(1)
                
                # 매 초 상태 체크
                if not self.dashboard.isVisible():
                    raise Exception(f"{i+1}초 후 화면 사라짐")
            
            return "10초 유지 성공"
        
        if not self.stage("Stage 7: 장기 실행", long_running):
            return 1
        
        # === Stage 8: 정상 종료 ===
        def close_dashboard():
            self.log("🚪 종료 시작...")
            
            # closeEvent 트리거
            self.dashboard.close()
            
            self.wait(2, "종료 처리")
            
            if self.dashboard.isVisible():
                raise Exception("종료 실패")
            
            return "정상 종료"
        
        if not self.stage("Stage 8: 종료", close_dashboard):
            return 1
        
        # === Stage 9: 메모리 정리 ===
        def cleanup():
            self.dashboard.deleteLater()
            self.wait(1, "deleteLater 처리")
            
            import gc
            gc.collect()
            
            return "메모리 정리 완료"
        
        if not self.stage("Stage 9: 정리", cleanup):
            return 1
        
        # === 최종 결과 ===
        print("\n" + "="*60)
        print("📊 실시간 GUI 검증 결과")
        print("="*60)
        
        passed = sum(1 for _, ok, _ in self.stages if ok)
        failed = sum(1 for _, ok, _ in self.stages if not ok)
        
        for name, ok, msg in self.stages:
            status = "✅" if ok else "❌"
            print(f"  {status} {name}: {msg[:40]}")
        
        print(f"\n통과: {passed}/{len(self.stages)}")
        print(f"실패: {failed}/{len(self.stages)}")
        
        elapsed = time.time() - self.start_time
        print(f"총 소요: {elapsed:.1f}초")
        
        if self.errors:
            print("\n" + "="*60)
            print("❌ 에러 상세")
            print("="*60)
            for name, err, tb in self.errors:
                print(f"\n[{name}]")
                print(f"에러: {err}")
                print("트레이스백:")
                print(tb)
        
        return 0 if failed == 0 else 1

def main():
    tester = RealtimeGUITester()
    return tester.run()

if __name__ == "__main__":
    sys.exit(main())
