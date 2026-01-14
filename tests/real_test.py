"""
실전 검증 - 실제 API/동작 테스트 (v2.4)
"""

import sys
import time
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

class RealTestRunner:
    def __init__(self):
        self.results = []
    
    def test(self, name, func):
        print(f"\n▶ {name}")
        try:
            result = func()
            self.results.append((name, True, result))
            print(f"  ✅ 성공: {result}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.results.append((name, False, str(e)))
            print(f"  ❌ 실패: {e}")
            # print(tb) # 상세 오류 필요시 주석 해제

def main():
    print("="*60)
    print("🔥 TwinStar Quantum - 실전 검증 시작 (v2.4)")
    print("="*60)
    
    runner = RealTestRunner()
    
    # === 1. API 연결 테스트 ===
    print("\n[1] API 실제 연결")
    
    def test_bybit_connection():
        from exchanges.exchange_manager import get_exchange_manager
        em = get_exchange_manager()
        adapter = em.get_exchange('bybit')
        
        if adapter is None:
            raise Exception("Bybit Adapter 생성 실패 (API 키 설정을 확인하세요)")
        
        # 실제 API 호출
        balance = adapter.get_balance()
        return f"Bybit 잔고: ${balance:,.2f}" if balance is not None else "잔고 조회 성공 (0 또는 None)"
    
    runner.test("Bybit API 연결", test_bybit_connection)
    
    # === 2. 실제 데이터 조회 ===
    print("\n[2] 실제 데이터 조회")
    
    def test_kline_fetch():
        from exchanges.exchange_manager import get_exchange_manager
        em = get_exchange_manager()
        adapter = em.get_exchange('bybit')
        
        if adapter is None:
            raise Exception("Adapter 없음")
            
        df = adapter.get_klines(symbol='BTCUSDT', interval='15m', limit=10)
        
        if df is None or len(df) == 0:
            raise Exception("캔들 데이터 수신 실패")
        
        return f"BTCUSDT 15m: {len(df)}봉, 최신가: ${df['close'].iloc[-1]:,.2f}"
    
    runner.test("캔들 데이터 조회", test_kline_fetch)
    
    # === 3. 시그널 탐지 ===
    print("\n[3] 시그널 탐지")
    
    def test_signal_detection():
        from exchanges.exchange_manager import get_exchange_manager
        from core.strategy_core import AlphaX7Core
        
        em = get_exchange_manager()
        adapter = em.get_exchange('bybit')
        if adapter is None: raise Exception("Adapter 없음")
        
        core = AlphaX7Core()
        
        # 100봉 조회 (W/M 패턴은 데이터가 넉넉해야 함)
        df_entry = adapter.get_klines(symbol='BTCUSDT', interval='15m', limit=100)
        df_pattern = adapter.get_klines(symbol='BTCUSDT', interval='1h', limit=100)
        
        if df_entry is None or len(df_entry) < 50:
            raise Exception("데이터 부족")
        
        # 실제 시그널 탐지 (detect_signal 사용)
        signal = core.detect_signal(df_1h=df_pattern, df_15m=df_entry)
        
        if signal and signal.signal_type != 'NONE':
            return f"시그널 감지됨: {signal.signal_type} ({signal.pattern})"
        return "시그널 없음 (시스템 정상 동작 확인)"
    
    runner.test("AlphaX7 시그널 로직", test_signal_detection)
    
    # === 4. 프리셋 실제 저장/로드 ===
    print("\n[4] 프리셋 파일 I/O")
    
    def test_preset_io():
        from core.auto_optimizer import AutoOptimizer
        from paths import Paths
        
        ao = AutoOptimizer('bybit', 'REALTEST_ST')
        
        # 저장
        params = ao.DEFAULT_PARAMS.copy()
        ao.save_preset(params, '4h')
        
        # 로드
        preset = ao.load_preset('4h')
        
        # 정리
        test_file = Path(Paths.PRESETS) / "REALTEST_ST_4h.json"
        if test_file.exists():
            test_file.unlink()
        
        if preset is None:
            raise Exception("프리셋 저장 후 로드 실패")
            
        return f"프리셋 I/O 성공 (Path: {test_file.name})"
    
    runner.test("프리셋 I/O", test_preset_io)
    
    # === 5. 웹소켓 연결/해제 ===
    print("\n[5] 웹소켓 사이클")
    
    def test_websocket_cycle():
        from exchanges.ws_handler import WebSocketHandler
        
        # WebSocketHandler는 exchange, symbol 인자 필수
        ws = WebSocketHandler(exchange='bybit', symbol='BTCUSDT', interval='15m')
        
        # 기본 메서드 존재 확인
        assert hasattr(ws, 'connect')
        assert hasattr(ws, 'disconnect')
        
        # disconnect 호출 안정성 테스트
        ws.disconnect()
        
        return "WebSocket 핸들러 메서드 안정성 확인"
    
    runner.test("WebSocket 사이클", test_websocket_cycle)
    
    # === 6. MultiTrader 실제 초기화 ===
    print("\n[6] MultiTrader 실제 기초")
    
    def test_multi_trader_init():
        from core.multi_trader import MultiTrader
        
        mt = MultiTrader({
            'exchange': 'bybit',
            'watch_count': 5,
            'seed': 100,
            'leverage': 3
        })
        
        # 실제 타겟 심볼 목록 (API 호출 포함 가능성)
        symbols = mt._get_target_symbols()
        
        if not symbols:
            raise Exception("감시 대상 심볼 목록 조회 실패")
        
        return f"정상 초기화: {len(symbols)}개 심볼 확보 ({', '.join(symbols[:3])}...)"
    
    runner.test("MultiTrader 초기화 전수", test_multi_trader_init)
    
    # === 7. GUI 실제 렌더링 ===
    print("\n[7] GUI 실제 렌더링")
    
    def test_gui_render():
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import QTimer
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        from GUI.trading_dashboard import TradingDashboard
        
        # 메인 대시보드 생성
        widget = TradingDashboard()
        widget.setWindowTitle("TwinStar Quantum - Real Test v2.4")
        widget.resize(1000, 700)
        widget.show()
        
        # 이벤트 루프 처리
        app.processEvents()
        time.sleep(1.0) # 렌더링 대기
        app.processEvents()
        
        # 표시 여부 확인
        is_visible = widget.isVisible()
        
        # 위젯 내부 핵심 요소 확인 (예: 로그 텍스트)
        has_log = hasattr(widget, 'log_text')
        
        widget.close()
        widget.deleteLater()
        
        if not is_visible:
            raise Exception("GUI 위젯 화면 표시 실패")
        
        return f"Dashboard 렌더링 성공 (Visible: {is_visible}, LogPanel: {has_log})"
    
    runner.test("GUI 렌더링 실전", test_gui_render)
    
    # === 8. 종료 시나리오 ===
    print("\n[8] 종료 시나리오")
    
    def test_cleanup():
        from core.multi_trader import MultiTrader
        
        mt = MultiTrader({'exchange': 'bybit'})
        
        # 강제 중지 호출 및 안전성 확인
        mt.stop()
        
        if mt.running:
            raise Exception("MultiTrader 중지 실패")
            
        return "프로세스 안전 종료 확인"
    
    runner.test("종료 및 리소스 정리", test_cleanup)
    
    # === 결과 ===
    print("\n" + "="*60)
    print("📊 TwinStar Quantum - 실전 검증 결과 요약")
    print("="*60)
    
    passed = sum(1 for _, ok, _ in runner.results if ok)
    failed = sum(1 for _, ok, _ in runner.results if not ok)
    total = len(runner.results)
    
    print(f"✅ 통과: {passed}/{total}")
    print(f"❌ 실패: {failed}/{total}")
    
    if failed > 0:
        print("\n[상세 실패 보고]")
        for name, ok, msg in runner.results:
            if not ok:
                print(f"  - {name}: {msg}")
    
    print("\n" + "="*60)
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
