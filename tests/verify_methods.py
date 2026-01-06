"""메서드 존재 검증"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

REQUIRED = {
    "core.multi_trader.MultiTrader": [
        "start", "stop", "_scan_signals", "_enter_position",
        "_has_preset", "_run_quick_optimize", "_get_adaptive_leverage",
        "_check_position", "_close_position", "get_stats"
    ],
    "core.auto_optimizer.AutoOptimizer": [
        "load_preset", "save_preset", "run_quick_optimize", "ensure_preset"
    ],
    "core.capital_manager.CapitalManager": [
        "get_trade_size", "update_after_trade", "switch_mode"
    ],
    "core.order_executor.OrderExecutor": [
        "place_order_with_retry", "close_position_with_retry", "set_leverage"
    ],
}

def run():
    """메서드 검증 실행"""
    import importlib
    
    passed = 0
    failed = 0
    errors = []
    
    for class_path, methods in REQUIRED.items():
        parts = class_path.rsplit(".", 1)
        mod_name, class_name = parts[0], parts[1]
        
        print(f"\n[{class_name}]")
        
        try:
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, class_name)
            
            for method in methods:
                if hasattr(cls, method):
                    print(f"  ✅ {method}")
                    passed += 1
                else:
                    print(f"  ❌ {method}: 없음")
                    failed += 1
                    errors.append((f"{class_name}.{method}", "메서드 없음"))
                    
        except Exception as e:
            print(f"  ❌ 클래스 로드 실패: {e}")
            failed += len(methods)
            errors.append((class_name, str(e)))
    
    return {'passed': passed, 'failed': failed, 'errors': errors}

if __name__ == "__main__":
    result = run()
    print(f"\n결과: {result['passed']}/{result['passed']+result['failed']}")
