
import sys
import os
import inspect
import json
import logging
from unittest.mock import MagicMock, patch
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).parent))

# ---------------------------------------------------------
# MOCK PyQt5 BEFORE IMPORTS
# ---------------------------------------------------------
# This allows importing GUI modules even if PyQt5 is not installed or no display
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtWidgets'] = MagicMock()
sys.modules['PyQt5.QtCore'] = MagicMock()
sys.modules['PyQt5.QtGui'] = MagicMock()
sys.modules['PyQt5.QtChart'] = MagicMock()

# Specific Mocks for QWidget used as base classes
sys.modules['PyQt5.QtWidgets'].QWidget = MagicMock
sys.modules['PyQt5.QtWidgets'].QMainWindow = MagicMock
sys.modules['PyQt5.QtWidgets'].QDialog = MagicMock

# Now we can safely import GUI modules
TradingDashboard = None
CoinRow = None
try:
    from GUI import trading_dashboard as td_module
    TradingDashboard = getattr(td_module, 'TradingDashboard', None)
    CoinRow = getattr(td_module, 'CoinRow', None)
except ImportError as e:
    print(f"Warning: Could not import TradingDashboard: {e}")

try:
    from GUI.dashboard_widgets import EquityCurveWidget
except ImportError:
    EquityCurveWidget = None

try:
    from core.strategy_core import AlphaX7Core
except ImportError:
    AlphaX7Core = None

try:
    from core.optimizer import BacktestOptimizer
except ImportError:
    BacktestOptimizer = None

try:
    from utils.preset_manager import PresetManager
except ImportError:
    PresetManager = None

try:
    from core.signal_processor import SignalProcessor
except ImportError:
    SignalProcessor = None

try:
    from core.position_manager import PositionManager
except ImportError:
    PositionManager = None

try:
    from exchanges.bybit_exchange import BybitExchange
except ImportError:
    BybitExchange = None
    
from config.parameters import PARAM_RANGES

results = {}

def check(name, condition, details=""):
    status = "OK" if condition else "FAIL"
    results[name] = {"status": status, "details": details}
    print(f"[{name}] {status} {details}")

print("=== STARTING GUI FUNCTION VERIFICATION ===")

# --- 1. Bot Start/Stop ---
if CoinRow:
    has_start = hasattr(CoinRow, 'start_clicked')
    has_stop = hasattr(CoinRow, 'stop_clicked')
    check("1. Bot Start/Stop", has_start and has_stop, f"CoinRow signals found")
else:
    check("1. Bot Start/Stop", False, "CoinRow missing")

# --- 2. Backtest ---
if AlphaX7Core:
    # AlphaX7Core has run_backtest usually
    has_backtest = hasattr(AlphaX7Core, 'run_backtest')
    check("2. Backtest Logic", has_backtest, f"run_backtest: {has_backtest}")
else:
    check("2. Backtest Logic", False, "AlphaX7Core missing")

# --- 3. Optimization ---
if BacktestOptimizer:
    has_opt = hasattr(BacktestOptimizer, 'optimize')
    has_ranges = len(PARAM_RANGES) > 0
    check("3. Optimization", has_opt and has_ranges, f"Method found: {has_opt}, Params: {len(PARAM_RANGES)}")
else:
    check("3. Optimization", False, "BacktestOptimizer missing")

# --- 4. Settings Save ---
if PresetManager:
    has_save = hasattr(PresetManager, 'save_preset')
    # Check config files
    config_exists = False
    for p in [r'C:\매매전략\config\parameters.py', r'C:\매매전략\config\settings.json']:
        if os.path.exists(p):
            config_exists = True
    check("4. Settings Save", has_save, f"save_preset: {has_save}, Config found: {config_exists}")
else:
    check("4. Settings Save", False, "PresetManager missing")

# --- 5. Chart Update ---
if EquityCurveWidget:
    # Check for update methods
    methods = [m for m in dir(EquityCurveWidget) if 'update' in m.lower() or 'plot' in m.lower()]
    check("5. Chart Update", len(methods) > 0, f"Found: {methods[:3]}")
else:
    check("5. Chart Update", False, "EquityCurveWidget missing")

# --- 6. Signal Display ---
if SignalProcessor:
    has_from_df = hasattr(SignalProcessor, 'add_patterns_from_df')
    check("6. Signal Display", has_from_df, f"add_patterns_from_df: {has_from_df}")
else:
    check("6. Signal Display", False, "SignalProcessor missing")

# --- 7. Position Display ---
if PositionManager:
    has_sync = hasattr(PositionManager, 'sync_with_exchange')
    check("7. Position Display", has_sync, f"sync_with_exchange: {has_sync}")
else:
    check("7. Position Display", False, "PositionManager missing")

# --- 8. Log Display ---
try:
    from core.unified_bot import setup_logging
    check("8. Log Display", callable(setup_logging), "setup_logging is callable")
except ImportError:
    check("8. Log Display", False, "unified_bot missing")

# --- 9. Exchange Connection ---
if BybitExchange:
    methods = [m for m in dir(BybitExchange) if 'connect' in m.lower()]
    check("9. Exchange State", len(methods) > 0, f"Found: {methods}")
else:
    check("9. Exchange State", False, "BybitExchange missing")

# --- 10. Error Notification ---
gui_files = [
    r'C:\매매전략\GUI\trading_dashboard.py',
    r'C:\매매전략\GUI\staru_main.py'
]
msg_box_found = False
for fpath in gui_files:
    if os.path.exists(fpath):
        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            if 'QMessageBox' in f.read():
                msg_box_found = True
                break
check("10. Error Notification", msg_box_found, "QMessageBox usage found")


print("\n" + "="*50)
print(f"{'ITEM':<20} | {'FUNCTION':<20} | {'RESULT':<6}")
print("="*50)
labels = [
    ("1", "Bot Start/Stop", "start_clicked"),
    ("2", "Backtest", "run_backtest()"),
    ("3", "Optimization", "optimize()"),
    ("4", "Save Settings", "save_preset()"),
    ("5", "Chart Update", "update_curve()"),
    ("6", "Signal Display", "display_signal()"),
    ("7", "Position Display", "sync_exchange()"),
    ("8", "Log Display", "logging"),
    ("9", "Exchange State", "connect()"),
    ("10", "Error Alert", "QMessageBox"),
]

for idx, label, func in labels:
    # Simple match
    keys = [k for k in results.keys() if k.startswith(idx + ".")]
    if keys:
        res = results[keys[0]]["status"]
        print(f"{idx:<2} | {label:<17} | {func:<17} | {res:^6}")
    else:
        print(f"{idx:<2} | {label:<17} | {func:<17} | {'MISS':^6}")

print("="*50)
