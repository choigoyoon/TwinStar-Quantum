"""
통합 테스트 - 전체 매매 흐름 시뮬레이션
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

class IntegrationTestRunner:
    def __init__(self):
        self.results = []
    
    def test(self, name: str, func) -> bool:
        try:
            result = func()
            self.results.append((name, True, None))
            print(f"  ✅ {name}")
            return True
        except Exception as e:
            self.results.append((name, False, str(e)[:100]))
            print(f"  ❌ {name}: {str(e)[:50]}")
            return False

def main():
    print("="*60)
    print("🔗 통합 테스트 시작")
    print("="*60)
    
    runner = IntegrationTestRunner()
    
    # === 시나리오 1: 프리셋 흐름 ===
    print("\n[시나리오 1] 프리셋 생성/로드 흐름")
    
    def test_preset_flow():
        from core.auto_optimizer import AutoOptimizer
        from paths import Paths
        
        ao = AutoOptimizer('bybit', 'TESTUSDT')
        
        # 1. 프리셋 없음 확인
        preset = ao.load_preset()
        
        # 2. 기본값으로 저장
        ao.save_preset(ao.DEFAULT_PARAMS, '4h', {'win_rate': 60})
        
        # 3. 다시 로드
        preset = ao.load_preset()
        assert preset is not None
        assert 'params' in preset
        
        # 4. 정리 (테스트 파일 삭제)
        test_file = Path(Paths.PRESETS) / "TESTUSDT_4h.json"
        if test_file.exists():
            test_file.unlink()
        
        return True
    runner.test("프리셋 생성→로드→삭제", test_preset_flow)
    
    # === 시나리오 2: 자본 관리 흐름 ===
    print("\n[시나리오 2] 자본 관리 흐름")
    
    def test_capital_flow():
        from core.capital_manager import CapitalManager
        
        cm = CapitalManager(initial_capital=1000, fixed_amount=100)
        
        # 1. 복리 모드
        cm.switch_mode('compound')
        size1 = cm.get_trade_size()
        
        # 2. 수익 반영
        cm.update_after_trade(50)  # +$50
        size2 = cm.get_trade_size()
        assert size2 > size1  # 복리: 시드 증가
        
        # 3. 고정 모드
        cm.switch_mode('fixed')
        size3 = cm.get_trade_size()
        assert size3 == 100  # 고정: 항상 100
        
        return True
    runner.test("복리/고정 모드 전환", test_capital_flow)
    
    # === 시나리오 3: 레버리지 계산 ===
    print("\n[시나리오 3] 차등 레버리지")
    
    def test_leverage_calc():
        from core.multi_trader import MultiTrader
        
        mt = MultiTrader({'leverage': 10})
        
        btc_lev = mt._get_adaptive_leverage('BTCUSDT')
        eth_lev = mt._get_adaptive_leverage('ETHUSDT')
        alt_lev = mt._get_adaptive_leverage('DOGEUSDT')
        
        assert btc_lev == 10  # 메이저: 기준
        assert eth_lev == 10  # 메이저: 기준
        assert alt_lev == 16  # 알트: 1.6배
        
        return True
    runner.test("BTC/알트 레버리지 차등", test_leverage_calc)
    
    # === 시나리오 4: MultiTrader 상태 ===
    print("\n[시나리오 4] MultiTrader 상태 관리")
    
    def test_multi_trader_state():
        from core.multi_trader import MultiTrader
        
        mt = MultiTrader({
            'exchange': 'bybit',
            'watch_count': 10,
            'seed': 100,
            'leverage': 5
        })
        
        # 초기 상태
        stats = mt.get_stats()
        assert 'watching' in stats
        assert 'pending' in stats
        assert 'active' in stats
        
        # 시작 안 함 → running = False
        assert mt.running == False
        
        return True
    runner.test("MultiTrader 초기 상태", test_multi_trader_state)
    
    # === 결과 ===
    print("\n" + "="*60)
    print("📊 통합 테스트 요약")
    print("="*60)
    
    passed = sum(1 for _, ok, _ in runner.results if ok)
    failed = sum(1 for _, ok, _ in runner.results if not ok)
    
    print(f"통과: {passed}")
    print(f"실패: {failed}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
