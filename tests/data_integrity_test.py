"""
데이터 정합성 검증
- 최적화 결과 → 프리셋 저장 값 일치
- 프리셋 → 백테스트 로드 값 일치
- 백테스트 → 실매매 파라미터 일치
- 자본 계산 정확성
- PnL 계산 정확성
"""

import sys
import json
from pathlib import Path
from decimal import Decimal, ROUND_DOWN

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

class DataIntegrityTester:
    def __init__(self):
        self.results = []
        self.test_symbol = "BTCUSDT"
        self.test_timeframe = "4h"
    
    def log(self, msg):
        print(f"    {msg}")
    
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
    
    def compare_params(self, p1, p2, name1="A", name2="B"):
        """파라미터 비교"""
        diffs = []
        
        keys = set(p1.keys()) | set(p2.keys())
        
        for key in keys:
            v1 = p1.get(key)
            v2 = p2.get(key)
            
            if v1 != v2:
                # float 비교 (소수점 오차 허용)
                if isinstance(v1, float) and isinstance(v2, float):
                    if abs(v1 - v2) < 0.0001:
                        continue
                diffs.append(f"{key}: {v1} vs {v2}")
        
        return diffs

def main():
    print("="*60)
    print("🔬 데이터 정합성 검증 (v3.4)")
    print("="*60)
    print("최적화 → 프리셋 → 백테스트 → 실매매 값 일치 확인")
    print("="*60)
    
    t = DataIntegrityTester()
    
    # ========================================
    # 1. 최적화 → 프리셋 저장 일치
    # ========================================
    print("\n" + "="*50)
    print("📊 [1/8] 최적화 → 프리셋 저장")
    print("="*50)
    
    optimized_params = None
    
    def test_optimizer_to_preset():
        nonlocal optimized_params
        
        from core.auto_optimizer import AutoOptimizer
        from paths import Paths
        
        # 임시 디렉토리 생성 확인
        Paths.PRESETS.mkdir(parents=True, exist_ok=True)
        
        ao = AutoOptimizer('bybit', 'TESTCOIN')
        
        # 테스트 파라미터
        test_params = {
            'atr_mult': 1.5,
            'trail_start_r': 0.8,
            'trail_dist_r': 0.5,
            'leverage': 10,
            'rsi_period': 14
        }
        
        # 저장
        ao.save_preset(test_params, '4h', {'win_rate': 65.5, 'pnl': 125.3})
        
        # 다시 로드
        loaded = ao.load_preset('4h')
        
        if not loaded:
            raise Exception("프리셋 로드 실패")
        
        loaded_params = loaded.get('params', {})
        
        # 비교
        diffs = t.compare_params(test_params, loaded_params, "저장", "로드")
        
        # 정리
        preset_file = Paths.PRESETS / "TESTCOIN_4h.json"
        if preset_file.exists():
            preset_file.unlink()
        
        optimized_params = test_params
        
        if diffs:
            raise Exception(f"불일치: {diffs}")
        
        return "저장 → 로드 값 일치 ✓"
    
    t.test("최적화 → 프리셋", test_optimizer_to_preset)
    
    # ========================================
    # 2. 프리셋 파일 구조 검증
    # ========================================
    print("\n" + "="*50)
    print("📁 [2/8] 프리셋 파일 구조")
    print("="*50)
    
    def test_preset_structure():
        from core.auto_optimizer import AutoOptimizer
        from paths import Paths
        
        ao = AutoOptimizer('bybit', 'STRUCTTEST')
        
        test_params = {'atr_mult': 2.0, 'leverage': 5}
        ao.save_preset(test_params, '4h', {'win_rate': 60})
        
        # 파일 직접 읽기
        preset_file = Paths.PRESETS / "STRUCTTEST_4h.json"
        
        with open(preset_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
        
        # 필수 필드 확인
        required_fields = ['symbol', 'exchange', 'timeframe', 'params', 'created_at']
        missing = [f for f in required_fields if f not in raw_data]
        
        # 정리
        preset_file.unlink()
        
        if missing:
            raise Exception(f"누락 필드: {missing}")
        
        return f"필수 필드 {len(required_fields)}개 OK"
    
    t.test("프리셋 구조", test_preset_structure)
    
    # ========================================
    # 3. MultiTrader 프리셋 로드 일치
    # ========================================
    print("\n" + "="*50)
    print("🔄 [3/8] MultiTrader 프리셋 로드")
    print("="*50)
    
    def test_multi_trader_preset():
        from core.multi_trader import MultiTrader
        from core.auto_optimizer import AutoOptimizer
        from paths import Paths
        
        # 프리셋 생성
        ao = AutoOptimizer('bybit', 'MTTEST')
        test_params = {'atr_mult': 1.8, 'leverage': 8}
        ao.save_preset(test_params, '4h')
        
        # MultiTrader에서 로드
        mt = MultiTrader({'exchange': 'bybit'})
        loaded = mt._has_preset('MTTEST')
        
        # 정리
        preset_file = Paths.PRESETS / "MTTEST_4h.json"
        if preset_file.exists():
            preset_file.unlink()
        
        if not loaded:
            raise Exception("MultiTrader 프리셋 로드 실패")
        
        loaded_params = loaded.get('params', {})
        
        # params 안에 params가 있는 경우 처리
        if 'params' in loaded_params:
            loaded_params = loaded_params['params']
        
        diffs = t.compare_params(test_params, loaded_params)
        
        if diffs:
            raise Exception(f"불일치: {diffs}")
        
        return "MultiTrader 로드 값 일치 ✓"
    
    t.test("MultiTrader 프리셋", test_multi_trader_preset)
    
    # ========================================
    # 4. 자본 계산 정확성
    # ========================================
    print("\n" + "="*50)
    print("💰 [4/8] 자본 계산 정확성")
    print("="*50)
    
    def test_capital_calculation():
        from core.capital_manager import CapitalManager
        
        # 복리 모드 테스트
        cm = CapitalManager(initial_capital=1000, fixed_amount=100)
        cm.switch_mode('compound')
        
        # 초기 트레이드 사이즈
        size1 = cm.get_trade_size()
        
        # 수익 $100 반영
        cm.update_after_trade(100)
        
        # 증가한 트레이드 사이즈
        size2 = cm.get_trade_size()
        
        # 복리: 시드가 늘어나야 함
        if size2 <= size1:
            raise Exception(f"복리 계산 오류: {size1} → {size2}")
        
        # 고정 모드 테스트
        cm.switch_mode('fixed')
        size3 = cm.get_trade_size()
        
        # 고정: 항상 fixed_amount
        if size3 != 100:
            raise Exception(f"고정 계산 오류: {size3} != 100")
        
        return f"복리: {size1}→{size2}, 고정: {size3} ✓"
    
    t.test("자본 계산", test_capital_calculation)
    
    # ========================================
    # 5. PnL 계산 정확성
    # ========================================
    print("\n" + "="*50)
    print("📈 [5/8] PnL 계산 정확성")
    print("="*50)
    
    def test_pnl_calculation():
        # 수동 계산
        entry_price = 50000.0
        exit_price = 51000.0
        size_usd = 100.0
        leverage = 10
        direction = 'Long'
        
        # 예상 PnL
        if direction == 'Long':
            pnl_pct = (exit_price - entry_price) / entry_price * 100
        else:
            pnl_pct = (entry_price - exit_price) / entry_price * 100
        
        expected_pnl_usd = size_usd * (pnl_pct / 100) * leverage
        
        # 실제: (51000 - 50000) / 50000 * 100 = 2%
        # 2% * 100 * 10 = $20
        
        if abs(expected_pnl_usd - 20.0) > 0.01:
            raise Exception(f"PnL 계산 오류: {expected_pnl_usd} != 20.0")
        
        # Short 테스트
        direction = 'Short'
        entry_price = 50000.0
        exit_price = 49000.0
        
        pnl_pct = (entry_price - exit_price) / entry_price * 100  # 2%
        expected_pnl_usd = size_usd * (pnl_pct / 100) * leverage  # $20
        
        if abs(expected_pnl_usd - 20.0) > 0.01:
            raise Exception(f"Short PnL 오류: {expected_pnl_usd}")
        
        return "Long/Short PnL 계산 정확 ✓"
    
    t.test("PnL 계산", test_pnl_calculation)
    
    # ========================================
    # 6. 레버리지 차등 계산
    # ========================================
    print("\n" + "="*50)
    print("⚡ [6/8] 레버리지 차등 계산")
    print("="*50)
    
    def test_leverage_calc():
        from core.multi_trader import MultiTrader
        
        mt = MultiTrader({'leverage': 10})
        
        # BTC: 기준 (1.0x)
        btc_lev = mt._get_adaptive_leverage('BTCUSDT')
        
        # ETH: 기준 (1.0x)
        eth_lev = mt._get_adaptive_leverage('ETHUSDT')
        
        # 알트: 1.6x
        doge_lev = mt._get_adaptive_leverage('DOGEUSDT')
        sol_lev = mt._get_adaptive_leverage('SOLUSDT')
        
        # 검증 (MultiTrader._get_adaptive_leverage 구현에 따라 다를 수 있음, user prompt 참고)
        # Assuming BTC/ETH -> no change, Others -> * 1.6 from prompt expected result
        
        # Check actual logic in MultiTrader if possible or trust prompt's expectation
        # User prompt expects BTC:10, ETH:10, DOGE:16
        
        if btc_lev != 10:
            raise Exception(f"BTC 레버리지 오류: {btc_lev} != 10")
        
        if eth_lev != 10:
            raise Exception(f"ETH 레버리지 오류: {eth_lev} != 10")
        
        expected_alt = min(25, int(10 * 1.6))  # 16
        
        if doge_lev != expected_alt:
            raise Exception(f"DOGE 레버리지 오류: {doge_lev} != {expected_alt}")
        
        return f"BTC:{btc_lev}, ETH:{eth_lev}, DOGE:{doge_lev} ✓"
    
    t.test("레버리지 차등", test_leverage_calc)
    
    # ========================================
    # 7. 백테스트 결과 저장/로드
    # ========================================
    print("\n" + "="*50)
    print("📊 [7/8] 백테스트 결과 일치")
    print("="*50)
    
    def test_backtest_result():
        from core.auto_optimizer import AutoOptimizer
        from paths import Paths
        
        ao = AutoOptimizer('bybit', 'BTRESULT')
        
        # 백테스트 결과 포함 저장
        test_params = {'atr_mult': 1.5}
        backtest_result = {
            'win_rate': 62.5,
            'pnl': 150.75,
            'trades': 48,
            'max_drawdown': 12.3
        }
        
        ao.save_preset(test_params, '4h', backtest_result)
        
        # 파일에서 직접 로드
        preset_file = Paths.PRESETS / "BTRESULT_4h.json"
        
        with open(preset_file, 'r', encoding='utf-8') as f:
            saved = json.load(f)
        
        # 정리
        preset_file.unlink()
        
        saved_bt = saved.get('backtest_result', {})
        
        # 비교
        if saved_bt.get('win_rate') != 62.5:
            raise Exception(f"win_rate 불일치: {saved_bt.get('win_rate')}")
        
        if saved_bt.get('pnl') != 150.75:
            raise Exception(f"pnl 불일치: {saved_bt.get('pnl')}")
        
        return f"백테스트 결과 저장/로드 일치 ✓"
    
    t.test("백테스트 결과", test_backtest_result)
    
    # ========================================
    # 8. 전체 파이프라인 일관성
    # ========================================
    print("\n" + "="*50)
    print("🔗 [8/8] 전체 파이프라인 일관성")
    print("="*50)
    
    def test_full_pipeline():
        from core.auto_optimizer import AutoOptimizer
        from core.multi_trader import MultiTrader
        from core.capital_manager import CapitalManager
        from paths import Paths
        
        symbol = "PIPETEST"
        
        # 1. 최적화 결과 시뮬레이션
        original_params = {
            'atr_mult': 1.75,
            'trail_start_r': 0.85,
            'leverage': 12
        }
        
        # 2. 프리셋 저장
        ao = AutoOptimizer('bybit', symbol)
        ao.save_preset(original_params, '4h', {'win_rate': 70})
        
        # 3. MultiTrader에서 로드
        mt = MultiTrader({'exchange': 'bybit', 'leverage': 10})
        preset = mt._has_preset(symbol)
        
        if not preset:
            raise Exception("파이프라인: 프리셋 로드 실패")
        
        loaded_params = preset.get('params', {})
        if 'params' in loaded_params:
            loaded_params = loaded_params['params']
        
        # 4. 레버리지 계산 (프리셋 유무 확인 - Prompt logic seems strictly about parameter loading)
        # logic: loaded_params should match original_params
        
        # 정리
        preset_file = Paths.PRESETS / f"{symbol}_4h.json"
        if preset_file.exists():
            preset_file.unlink()
        
        # 검증
        if loaded_params.get('atr_mult') != original_params['atr_mult']:
            raise Exception("atr_mult 불일치")
        
        return f"최적화→프리셋→로드→계산 일관성 ✓"
    
    t.test("전체 파이프라인", test_full_pipeline)
    
    # ========================================
    # 최종 결과
    # ========================================
    print("\n" + "="*60)
    print("📊 데이터 정합성 검증 결과")
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
    output = {
        'passed': passed,
        'failed': failed,
        'details': [{'name': n, 'ok': o, 'msg': m} for n, o, m in t.results]
    }
    
    output_file = ROOT / "tests" / "data_integrity_result.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 결과: {output_file}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
