import sys
import os

print("🔹 Python Path:", sys.executable)
print("🔹 Current Dir:", os.getcwd())

def check(module_name):
    try:
        __import__(module_name)
        print(f"✅ {module_name:<30} OK")
        return True
    except Exception as e:
        print(f"❌ {module_name:<30} FAIL: {e}")
        return False

print("\n[PHASE 1] Utils Check (Recent Change)")
check('utils')
check('utils.data_utils')
check('utils.preset_manager')

print("\n[PHASE 2] Core Check")
check('core.strategy_core')
check('core.unified_bot')
check('core.optimizer')

print("\n[PHASE 3] Exchange Check")
check('exchanges.bybit_exchange')
check('exchanges.binance_exchange')
check('exchanges.exchange_manager')

print("\n[PHASE 4] Storage Check")
check('storage.secure_storage')
check('storage.trade_storage')

print("\n[PHASE 5] GUI Check")
# GUI는 경로 의존성이 있을 수 있어 sys.path에 GUI 추가하지 않고 직접 모듈명 테스트
# (staru_main.py 등 내부적으로 경로 설정이 있으나, 외부에서 import 시 경로가 맞아야 함)
check('GUI.trading_dashboard')
check('GUI.backtest_widget')
check('GUI.settings_widget')
check('GUI.optimization_widget')
check('GUI.staru_main')

print("\n🎉 Import Test Completed")
