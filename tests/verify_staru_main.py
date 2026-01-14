"""
staru_main.py 전체 검증
- 임포트 체인 검증
- 클래스/메서드 검증
- GUI 컴포넌트 검증
- 실시간 동작 검증
- 종료 안정성 검증
"""

import sys
import time
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

class StaruMainVerifier:
    def __init__(self):
        self.results = []
        self.errors = []
        self.app: Any = None
        self.main_window: Any = None
    
    def log(self, msg):
        print(f"  {msg}")
    
    def test(self, name, func):
        print(f"\n▶ {name}")
        try:
            result = func()
            self.results.append((name, True, result))
            self.log(f"✅ {result}")
            return True
        except Exception as e:
            self.results.append((name, False, str(e)))
            self.errors.append((name, str(e), traceback.format_exc()))
            self.log(f"❌ {e}")
            return False
    
    def process(self, ms=100):
        if self.app:
            for _ in range(ms // 10):
                self.app.processEvents()
                time.sleep(0.01)

def main():
    print("="*60)
    print("🔍 staru_main.py 전체 검증 (v3.1)")
    print("="*60)
    
    v = StaruMainVerifier()
    
    # ========================================
    # 1. 임포트 체인 검증
    # ========================================
    print("\n" + "="*50)
    print("📦 [1/7] 임포트 체인 검증")
    print("="*50)
    
    def test_core_imports():
        imports = []
        
        # staru_main.py가 사용하는 core 모듈
        from core.strategy_core import AlphaX7Core
        imports.append("AlphaX7Core")
        
        from core.capital_manager import CapitalManager
        imports.append("CapitalManager")
        
        from core.multi_trader import MultiTrader
        imports.append("MultiTrader")
        
        from core.auto_optimizer import AutoOptimizer
        imports.append("AutoOptimizer")
        
        from core.order_executor import OrderExecutor
        imports.append("OrderExecutor")
        
        return f"{len(imports)}개 core 모듈 OK"
    v.test("Core 모듈", test_core_imports)
    
    def test_exchange_imports():
        imports = []
        
        from exchanges.exchange_manager import ExchangeManager
        imports.append("ExchangeManager")
        
        from exchanges.bybit_exchange import BybitExchange
        imports.append("BybitExchange")
        
        from exchanges.ws_handler import WebSocketHandler
        imports.append("WebSocketHandler")
        
        return f"{len(imports)}개 exchange 모듈 OK"
    v.test("Exchange 모듈", test_exchange_imports)
    
    def test_gui_imports():
        imports = []
        
        from GUI.trading_dashboard import TradingDashboard
        imports.append("TradingDashboard")
        
        from GUI.multi_trade_widget import MultiTradeWidget
        imports.append("MultiTradeWidget")
        
        from GUI.single_trade_widget import SingleTradeWidget
        imports.append("SingleTradeWidget")
        
        return f"{len(imports)}개 GUI 모듈 OK"
    v.test("GUI 모듈", test_gui_imports)
    
    def test_util_imports():
        imports = []
        
        from utils.indicators import calculate_rsi, calculate_atr
        imports.append("indicators")
        
        from utils.helpers import safe_float
        imports.append("helpers")
        
        from paths import Paths
        imports.append("Paths")
        
        return f"{len(imports)}개 util 모듈 OK"
    v.test("Util 모듈", test_util_imports)
    
    # ========================================
    # 2. 클래스/메서드 검증
    # ========================================
    print("\n" + "="*50)
    print("🔧 [2/7] 클래스/메서드 검증")
    print("="*50)
    
    def test_multi_trader_methods():
        from core.multi_trader import MultiTrader
        
        required = [
            "start", "stop", "_scan_signals", "_enter_position",
            "_has_preset", "_run_quick_optimize", "_get_adaptive_leverage",
            "_check_position", "_close_position", "get_stats"
        ]
        
        missing = [m for m in required if not hasattr(MultiTrader, m)]
        
        if missing:
            raise Exception(f"누락: {missing}")
        
        return f"{len(required)}개 메서드 OK"
    v.test("MultiTrader 메서드", test_multi_trader_methods)
    
    def test_auto_optimizer_methods():
        from core.auto_optimizer import AutoOptimizer
        
        required = ["load_preset", "save_preset", "run_quick_optimize", "ensure_preset"]
        missing = [m for m in required if not hasattr(AutoOptimizer, m)]
        
        if missing:
            raise Exception(f"누락: {missing}")
        
        return f"{len(required)}개 메서드 OK"
    v.test("AutoOptimizer 메서드", test_auto_optimizer_methods)
    
    def test_capital_manager_methods():
        from core.capital_manager import CapitalManager
        
        required = ["get_trade_size", "update_after_trade", "switch_mode"]
        missing = [m for m in required if not hasattr(CapitalManager, m)]
        
        if missing:
            raise Exception(f"누락: {missing}")
        
        return f"{len(required)}개 메서드 OK"
    v.test("CapitalManager 메서드", test_capital_manager_methods)
    
    # ========================================
    # 3. 경로 검증
    # ========================================
    print("\n" + "="*50)
    print("📁 [3/7] 경로 검증")
    print("="*50)
    
    def test_paths():
        from paths import Paths
        
        checks = []
        
        assert isinstance(Paths.ROOT, Path), "ROOT not Path"
        checks.append("ROOT")
        
        assert isinstance(Paths.CONFIG, Path), "CONFIG not Path"
        checks.append("CONFIG")
        
        assert isinstance(Paths.PRESETS, Path), "PRESETS not Path"
        checks.append("PRESETS")
        
        assert isinstance(Paths.CACHE, Path), "CACHE not Path"
        checks.append("CACHE")
        
        return f"{len(checks)}개 경로 OK (pathlib.Path)"
    v.test("Paths 검증", test_paths)
    
    # ========================================
    # 4. PyQt5 초기화
    # ========================================
    print("\n" + "="*50)
    print("🖥️ [4/7] PyQt5 초기화")
    print("="*50)
    
    def test_pyqt5():
        from PyQt6.QtWidgets import QApplication
        v.app = QApplication.instance() or QApplication(sys.argv)
        return "QApplication 준비"
    v.test("PyQt5 초기화", test_pyqt5)
    
    # ========================================
    # 5. staru_main.py 로드 및 실행
    # ========================================
    print("\n" + "="*50)
    print("🚀 [5/7] staru_main.py 로드")
    print("="*50)
    
    def test_staru_main_import():
        from GUI.staru_main import StarUWindow
        return "StarUWindow 클래스 로드 OK"
    v.test("staru_main 임포트", test_staru_main_import)
    
    def test_main_window_create():
        from GUI.staru_main import StarUWindow
        v.main_window = StarUWindow()
        return "StarUWindow 인스턴스 생성 OK"
    v.test("MainWindow 생성", test_main_window_create)
    
    def test_main_window_show():
        if not v.main_window:
            raise Exception("MainWindow 없음")
        
        v.main_window.show()
        v.process(500)
        
        if not v.main_window.isVisible():
            raise Exception("화면 표시 실패")
        
        size = f"{v.main_window.width()}x{v.main_window.height()}"
        return f"화면 표시 OK ({size})"
    v.test("MainWindow 표시", test_main_window_show)
    
    # ========================================
    # 6. 실시간 동작 검증
    # ========================================
    print("\n" + "="*50)
    print("⚡ [6/7] 실시간 동작 검증")
    print("="*50)
    
    def test_timers():
        if not v.main_window:
            raise Exception("MainWindow 없음")
        
        from PyQt6.QtCore import QTimer
        
        timers = []
        for attr in dir(v.main_window):
            obj = getattr(v.main_window, attr, None)
            if isinstance(obj, QTimer):
                timers.append((attr, obj.isActive()))
        
        active = sum(1 for _, a in timers if a)
        return f"타이머 {active}/{len(timers)} 활성"
    v.test("타이머 상태", test_timers)
    
    def test_threads():
        if not v.main_window:
            raise Exception("MainWindow 없음")
        
        from PyQt6.QtCore import QThread
        
        threads = []
        for attr in dir(v.main_window):
            obj = getattr(v.main_window, attr, None)
            if isinstance(obj, QThread):
                threads.append((attr, obj.isRunning()))
        
        running = sum(1 for _, r in threads if r)
        return f"스레드 {running}/{len(threads)} 실행"
    v.test("스레드 상태", test_threads)
    
    def test_long_running():
        if not v.main_window:
            raise Exception("MainWindow 없음")
        
        print("    📺 10초 유지 테스트...")
        
        for i in range(10):
            v.process(1000)
            
            if not v.main_window.isVisible():
                raise Exception(f"{i+1}초 후 화면 사라짐")
            
            print(f"    {i+1}/10초 OK")
        
        return "10초 유지 성공"
    v.test("장기 실행", test_long_running)
    
    # ========================================
    # 7. 종료 안정성 검증
    # ========================================
    print("\n" + "="*50)
    print("🚪 [7/7] 종료 안정성 검증")
    print("="*50)
    
    def test_close():
        if not v.main_window:
            raise Exception("MainWindow 없음")
        
        v.main_window.close()
        v.process(1000)
        
        if v.main_window.isVisible():
            raise Exception("종료 실패")
        
        return "정상 종료"
    v.test("종료 처리", test_close)
    
    def test_cleanup():
        if v.main_window:
            v.main_window.deleteLater()
        
        v.process(500)
        
        import gc
        gc.collect()
        
        return "메모리 정리 완료"
    v.test("메모리 정리", test_cleanup)
    
    # ========================================
    # 최종 결과
    # ========================================
    print("\n" + "="*60)
    print("📊 staru_main.py 전체 검증 결과")
    print("="*60)
    
    passed = sum(1 for _, ok, _ in v.results if ok)
    failed = sum(1 for _, ok, _ in v.results if not ok)
    
    for name, ok, msg in v.results:
        status = "✅" if ok else "❌"
        print(f"  {status} {name}: {msg[:50]}")
    
    print("-"*60)
    print(f"  통과: {passed}/{len(v.results)}")
    print(f"  실패: {failed}/{len(v.results)}")
    print(f"  성공률: {passed/(passed+failed)*100:.1f}%")
    
    if v.errors:
        print("\n" + "="*60)
        print("❌ 에러 상세")
        print("="*60)
        for name, err, tb in v.errors:
            print(f"\n[{name}]")
            print(f"에러: {err}")
    
    # JSON 저장
    import json
    output = {
        'target': 'GUI/staru_main.py',
        'passed': passed,
        'failed': failed,
        'details': [{'name': n, 'ok': o, 'msg': m} for n, o, m in v.results]
    }
    
    output_file = Path(__file__).parent / "staru_main_verify.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 상세 결과: {output_file}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
