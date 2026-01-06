import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    checks = [
        ("GUI.trading_dashboard", ["UnifiedBot", "CapitalManager", "OrderExecutor"]),
        ("GUI.optimization_widget", ["Optimizer", "AlphaX7Core"]),
        ("GUI.backtest_widget", ["UnifiedBacktest", "AlphaX7Core"]),
        ("GUI.settings_widget", ["ExchangeManager"]),
    ]
    
    results = []
    for module_path, names in checks:
        print(f"\nChecking {module_path}:")
        try:
            mod = __import__(module_path, fromlist=names)
            for name in names:
                if hasattr(mod, name):
                    print(f"  [OK] {name}")
                    results.append((module_path, name, True))
                else:
                    # Some might be imported but not exposed if they are used internally
                    # Let's check actually importing them directly too
                    print(f"  [??] Checking direct import for {name}...")
                    try:
                        # This is a bit tricky, let's just use the fromlist check
                        print(f"  [FAIL] {name} not found in {module_path}")
                        results.append((module_path, name, False))
                    except:
                        pass
        except Exception as e:
            print(f"  [ERROR] Failed to import {module_path}: {e}")
            results.append((module_path, "MODULE", False))
            
    return results

if __name__ == "__main__":
    # Mocking QWidget etc to avoid GUI dependency if possible
    # But GUI files usually import PyQt6. Main thing is verifying the search paths and syntax.
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication([]) # Might be needed for some __init__ or static calls
    except ImportError:
        print("PyQt6 not found, some imports might fail if they trigger GUI logic at top level.")
        
    test_imports()
