"""모듈 임포트 검증"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

MODULES = {
    'core': [
        "core.auto_optimizer",
        "core.capital_manager", 
        "core.multi_trader",
        "core.order_executor",
        "core.pnl_tracker",
        "core.strategy_core",
        "core.trade_common",
    ],
    'exchanges': [
        "exchanges.exchange_manager",
        "exchanges.binance_exchange",
        "exchanges.bybit_exchange",
        "exchanges.ws_handler",
    ],
    'utils': [
        "utils.indicators",
        "utils.helpers",
        # "utils.data_utils", #Renamed in previous steps, checking implementation plans or recent files might be safer, but user prompt says data_utils. I'll stick to prompt but be wary.
        # Actually viewed_files earlier showed utils.data_utils usage in GUI/backtest_widget.py so it probably exists.
        "utils.data_utils",
    ],
    'gui': [
        "GUI.staru_main",
        "GUI.trading_dashboard",
        "GUI.multi_trade_widget",
    ],
}

def run():
    """모듈 검증 실행"""
    import importlib
    
    passed = 0
    failed = 0
    errors = []
    
    for category, modules in MODULES.items():
        print(f"\n[{category.upper()}]")
        
        for mod_name in modules:
            try:
                importlib.import_module(mod_name)
                print(f"  ✅ {mod_name}")
                passed += 1
            except Exception as e:
                print(f"  ❌ {mod_name}: {str(e)[:40]}")
                failed += 1
                errors.append((mod_name, str(e)))
    
    return {'passed': passed, 'failed': failed, 'errors': errors}

if __name__ == "__main__":
    result = run()
    print(f"\n결과: {result['passed']}/{result['passed']+result['failed']}")
