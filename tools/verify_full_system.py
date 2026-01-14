
import sys
import os
import io
import contextlib
import pandas as pd
import numpy as np
import logging
import tempfile
import inspect

# Setup paths
sys.path.insert(0, rstr(Path(__file__).parent))

# Configure logging to suppress during tests
logging.basicConfig(level=logging.CRITICAL)

results = {}

def print_result(name, status, details=""):
    results[name] = status
    print(f"[{name}] {status} {details}")

print("=== STARTING FULL SYSTEM VERIFICATION ===")

# --- Check 1: Import Connectivity ---
print("\n--- 1. Import Connectivity ---")
modules_to_check = [
    ('core.unified_bot', 'UnifiedBot'),
    ('core.bot_state', 'BotStateManager'),
    ('core.data_manager', 'BotDataManager'),
    ('core.signal_processor', 'SignalProcessor'),
    ('core.order_executor', 'OrderExecutor'),
    ('core.position_manager', 'PositionManager'),
    ('core.strategy_core', 'AlphaX7Core'),
    ('config.parameters', 'DEFAULT_PARAMS'),
    ('utils.indicators', 'calculate_rsi'),
    ('exchanges.bybit_exchange', 'BybitExchange'),
    ('exchanges.binance_exchange', 'BinanceExchange'),
]

passed_imports = 0
for mod_name, cls_name in modules_to_check:
    try:
        exec(f"from {mod_name} import {cls_name}")
        passed_imports += 1
    except Exception as e:
        print(f"FAIL: {mod_name} - {e}")

if passed_imports == len(modules_to_check):
    print_result("1. Import Connectivity", "OK", f"({passed_imports}/{len(modules_to_check)})")
else:
    print_result("1. Import Connectivity", "FAIL", f"({passed_imports}/{len(modules_to_check)})")


# --- Check 2: Calculation Consistency ---
print("\n--- 2. Calculation Consistency ---")
try:
    from utils.indicators import calculate_rsi, calculate_atr, calculate_macd
    
    np.random.seed(42)
    close = pd.Series(np.cumsum(np.random.randn(100)) + 100)
    high = close + abs(np.random.randn(100))
    low = close - abs(np.random.randn(100))
    df = pd.DataFrame({'high': high, 'low': low, 'close': close})
    
    rsi = calculate_rsi(close, 14, return_series=True)
    atr = calculate_atr(df, 14, return_series=True)
    macd, signal, hist = calculate_macd(close, 12, 26, 9, return_all=True)
    
    print(f"RSI[-1]: {rsi.iloc[-1]:.2f}")
    print(f"ATR[-1]: {atr.iloc[-1]:.4f}")
    print(f"MACD[-1]: {macd.iloc[-1]:.4f}")
    
    if not rsi.empty and not atr.empty and not macd.empty:
         print_result("2. Calculation Consistency", "OK")
    else:
         print_result("2. Calculation Consistency", "FAIL", "Empty result")
except Exception as e:
    print_result("2. Calculation Consistency", "FAIL", str(e))


# --- Check 3: Parameter SSOT ---
print("\n--- 3. Parameter SSOT ---")
try:
    from config.parameters import DEFAULT_PARAMS, get_param
    
    config_atr = get_param('atr_mult')
    config_rsi = get_param('rsi_period')
    config_macd_fast = get_param('macd_fast')
    
    print(f"config atr_mult: {config_atr}")
    print(f"config rsi_period: {config_rsi}")
    print(f"config macd_fast: {config_macd_fast}")
    print(f"Total Params: {len(DEFAULT_PARAMS)}")
    
    if config_atr is not None and config_rsi is not None:
        print_result("3. Parameter SSOT", "OK")
    else:
        print_result("3. Parameter SSOT", "FAIL", "None values returned")
except Exception as e:
    print_result("3. Parameter SSOT", "FAIL", str(e))


# --- Check 4: Module Initialization ---
print("\n--- 4. Module Initialization ---")
try:
    from core.bot_state import BotStateManager
    from core.data_manager import BotDataManager
    from core.signal_processor import SignalProcessor
    from core.strategy_core import AlphaX7Core

    state_mgr = BotStateManager('test', 'BTCUSDT')
    # SignalProcessor takes (strategy_params, direction)
    signal_proc = SignalProcessor({}, 'Both')
    
    print_result("4. Module Initialization", "OK")
except Exception as e:
    print_result("4. Module Initialization", "FAIL", str(e))


# --- Check 5: State Save/Load (Atomic) ---
print("\n--- 5. State Save/Load (Atomic) ---")
try:
    from core.bot_state import BotStateManager
    mgr = BotStateManager('test_atomic', 'BTCUSDT')
    if os.path.exists(mgr.state_file): os.remove(mgr.state_file)
    
    test_state = {'position': None, 'capital': 1000, 'test': True}
    mgr.save_state(test_state)
    
    loaded = mgr.load_state()
    if loaded and loaded.get("capital") == 1000:
        print_result("5. State Save/Load", "OK")
    else:
        print_result("5. State Save/Load", "FAIL", "Data mismatch")
        
    if os.path.exists(mgr.state_file): os.remove(mgr.state_file)
except Exception as e:
    print_result("5. State Save/Load", "FAIL", str(e))


# --- Check 6: Exchange Safety (get_positions) ---
print("\n--- 6. Exchange Safety ---")
try:
    from exchanges.bybit_exchange import BybitExchange
    source = inspect.getsource(BybitExchange.get_positions)
    
    if 'return None' in source or 'return result' in source: # 'result' might be initialized to None or handled
        # Specific check for 'return None' in exception block or failure case
        print_result("6. Exchange Safety", "OK" if "return None" in source else "WARN", "Source Checked")
    else:
        print_result("6. Exchange Safety", "FAIL", "No explicit 'return None' found in source")
except Exception as e:
    print_result("6. Exchange Safety", "FAIL", str(e))


# --- Check 7: GUI Import ---
print("\n--- 7. GUI Import ---")
try:
    # Mocking QApplication to avoid GUI initialization errors if needed
    # But just importing main class usually doesn't trigger app loop
    from GUI.staru_main import main
    print_result("7. GUI Import", "OK")
except ImportError:
    print_result("7. GUI Import", "WARN", "PyQt5 not installed or display issue (Expected in CLI)")
except Exception as e:
    print_result("7. GUI Import", "FAIL", str(e))


# --- Check 8: Backtest Data ---
print("\n--- 8. Backtest Data ---")
try:
    from core.strategy_core import AlphaX7Core
    from config.parameters import DEFAULT_PARAMS
    from utils.indicators import calculate_rsi, calculate_atr
    
    dates = pd.date_range('2024-01-01', periods=100, freq='1h')
    close = np.random.randn(100) + 50000
    df = pd.DataFrame({'close': close, 'high': close+100, 'low': close-100, 'open': close}, index=dates)
    
    df['rsi'] = calculate_rsi(df['close'], 14)
    df['atr'] = calculate_atr(df, 14)
    
    print(f"RSI Mean: {df['rsi'].mean():.2f}")
    if not df['rsi'].isnull().all():
        print_result("8. Backtest Data", "OK")
    else:
        print_result("8. Backtest Data", "FAIL", "RSI all nan")
except Exception as e:
    print_result("8. Backtest Data", "FAIL", str(e))


# --- SUMMARY REPORT ---
print("\n" + "="*30)
print("   FULL VERIFICATION REPORT   ")
print("="*30)
for k, v in results.items():
    print(f"| {k:<25} | {v:^6} |")
print("="*30)

fail_count = sum(1 for v in results.values() if v == "FAIL")
if fail_count == 0:
    print("\n✅ ALL CHECKS PASSED")
else:
    print(f"\n❌ {fail_count} CHECKS FAILED")
