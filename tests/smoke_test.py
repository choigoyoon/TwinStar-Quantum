"""
스모크 테스트 - 핵심 객체 생성 및 기본 메서드 호출
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

class SmokeTestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def test(self, name: str, func):
        try:
            func()
            self.passed += 1
            print(f"  ✅ {name}")
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            self.failed += 1
            self.errors.append((name, tb))
            print(f"  ❌ {name}: {str(e)[:50]}")

def main():
    print("="*60)
    print("💨 스모크 테스트 시작")
    print("="*60)
    
    runner = SmokeTestRunner()
    
    # === Core 모듈 ===
    print("\n[CORE]")
    
    def test_multi_trader():
        from core.multi_trader import MultiTrader
        mt = MultiTrader({'exchange': 'bybit', 'seed': 100})
        assert hasattr(mt, 'start')
        assert hasattr(mt, 'stop')
        assert mt.get_stats() is not None
    runner.test("MultiTrader 생성", test_multi_trader)
    
    def test_auto_optimizer():
        from core.auto_optimizer import AutoOptimizer
        ao = AutoOptimizer('bybit', 'BTCUSDT')
        assert hasattr(ao, 'load_preset')
        assert hasattr(ao, 'ensure_preset')
    runner.test("AutoOptimizer 생성", test_auto_optimizer)
    
    def test_capital_manager():
        from core.capital_manager import CapitalManager
        cm = CapitalManager(initial_capital=1000)
        assert cm.get_trade_size() > 0
        cm.switch_mode('fixed')
        cm.switch_mode('compound')
    runner.test("CapitalManager 생성/전환", test_capital_manager)
    
    def test_strategy_core():
        from core.strategy_core import AlphaX7Core
        core = AlphaX7Core()
        assert hasattr(core, 'detect_signal')
    runner.test("AlphaX7Core 생성", test_strategy_core)
    
    # === Exchanges ===
    print("\n[EXCHANGES]")
    
    def test_exchange_manager():
        from exchanges.exchange_manager import ExchangeManager
        em = ExchangeManager()
        assert hasattr(em, 'get_exchange')
    runner.test("ExchangeManager 생성", test_exchange_manager)
    
    def test_ws_handler():
        from exchanges.ws_handler import WebSocketHandler
        ws = WebSocketHandler(exchange='bybit', symbol='BTCUSDT', interval='15m')
        assert hasattr(ws, 'connect')
        assert hasattr(ws, 'disconnect')
    runner.test("WebSocketHandler 생성", test_ws_handler)
    
    # === Paths ===
    print("\n[PATHS]")
    
    def test_paths():
        from paths import Paths
        # Paths.ROOT가 Path 객체이며 존재하는지 확인
        p = Path(Paths.ROOT)
        assert p.exists()
        assert isinstance(Paths.PRESETS, Path)
        assert isinstance(Paths.CACHE, Path)
    runner.test("Paths 검증", test_paths)
    
    # === 결과 ===
    print("\n" + "="*60)
    print("📊 스모크 테스트 요약")
    print("="*60)
    print(f"통과: {runner.passed}")
    print(f"실패: {runner.failed}")
    
    if runner.errors:
        print("\n실패 상세:")
        for name, err in runner.errors:
            print(f"  - {name}: {err}")
    
    return 0 if runner.failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
