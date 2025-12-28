# system_bloodflow_check.py
# 저장 위치: c:\매매전략\system_bloodflow_check.py
"""
TwinStar Quantum - 전체 시스템 혈관 검증
EXE 빌드 전 필수 체크
"""

import sys
import os
import traceback

# 경로 설정
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)
sys.path.insert(0, os.path.join(PROJECT_ROOT, 'GUI'))

print("=" * 70)
print("TwinStar Quantum - System Bloodflow Check")
print(f"Project Path: {PROJECT_ROOT}")
print("=" * 70)

results = {
    'pass': [],
    'fail': [],
    'warn': []
}

def check(name, func):
    """검증 실행 및 결과 기록"""
    try:
        result = func()
        if result:
            results['pass'].append((name, result))
            print(f"[PASS] {name}")
            if isinstance(result, dict):
                for k, v in result.items():
                    print(f"       {k}: {v}")
            return result
        else:
            results['warn'].append((name, "No result"))
            print(f"[WARN] {name}: No result")
            return None
    except Exception as e:
        results['fail'].append((name, str(e), traceback.format_exc()))
        print(f"[FAIL] {name}")
        print(f"       {e}")
        return None


# ============================================================
print("\n" + "=" * 70)
print("PHASE 1: Core Module Import Check")
print("=" * 70 + "\n")

def check_strategy_core():
    from core.strategy_core import AlphaX7Core
    core = AlphaX7Core()
    methods = ['detect_signal', 'run_backtest', 'manage_position_realtime']
    found = [m for m in methods if hasattr(core, m)]
    missing = [m for m in methods if not hasattr(core, m)]
    if missing:
        raise Exception(f"Methods missing: {missing}")
    return {'class': 'AlphaX7Core', 'methods': len(found)}

def check_optimizer():
    from core.optimizer import BacktestOptimizer, generate_full_grid, generate_fast_grid
    grid = generate_fast_grid('1h', 20)
    return {'class': 'BacktestOptimizer', 'grid_keys': list(grid.keys())[:5]}

def check_unified_bot():
    from core.unified_bot import UnifiedBot
    methods = ['run', 'execute_entry']
    found = [m for m in methods if hasattr(UnifiedBot, m)]
    return {'class': 'UnifiedBot', 'methods': len(found)}

check("1.1 core.strategy_core", check_strategy_core)
check("1.2 core.optimizer", check_optimizer)
check("1.3 core.unified_bot", check_unified_bot)


# ============================================================
print("\n" + "=" * 70)
print("PHASE 2: Exchange Module Check")
print("=" * 70 + "\n")

def check_exchange_manager():
    from exchanges.exchange_manager import get_exchange_manager, connect_exchange
    return {'functions': ['get_exchange_manager', 'connect_exchange']}

def check_bybit():
    from exchanges.bybit_exchange import BybitExchange
    methods = ['connect', 'get_klines', 'place_market_order', 'set_leverage']
    found = [m for m in methods if hasattr(BybitExchange, m)]
    return {'class': 'BybitExchange', 'methods': len(found)}

def check_binance():
    from exchanges.binance_exchange import BinanceExchange
    methods = ['connect', 'get_klines', 'place_market_order', 'set_leverage']
    found = [m for m in methods if hasattr(BinanceExchange, m)]
    return {'class': 'BinanceExchange', 'methods': len(found)}

def check_secure_storage_in_exchange():
    """Exchange -> SecureStorage connection"""
    from exchanges.binance_exchange import BinanceExchange
    import inspect
    source = inspect.getsourcefile(BinanceExchange)
    with open(source, 'r', encoding='utf-8') as f:
        content = f.read()
    has_secure = 'secure_storage' in content or 'get_secure_storage' in content
    return {'binance->secure_storage': has_secure}

check("2.1 exchanges.exchange_manager", check_exchange_manager)
check("2.2 exchanges.bybit_exchange", check_bybit)
check("2.3 exchanges.binance_exchange", check_binance)
check("2.4 exchange->storage connection", check_secure_storage_in_exchange)


# ============================================================
print("\n" + "=" * 70)
print("PHASE 3: Storage Module Check")
print("=" * 70 + "\n")

def check_secure_storage():
    from storage.secure_storage import get_secure_storage, SecureKeyStorage
    storage = get_secure_storage()
    methods = ['get_exchange_keys', 'load_api_keys']
    found = [m for m in methods if hasattr(storage, m)]
    return {'singleton': True, 'methods': len(found)}

def check_trade_storage():
    from storage.trade_storage import get_trade_storage
    return {'factory': 'get_trade_storage'}

def check_state_storage():
    from storage.state_storage import StateStorage
    return {'class': 'StateStorage'}

check("3.1 storage.secure_storage", check_secure_storage)
check("3.2 storage.trade_storage", check_trade_storage)
check("3.3 storage.state_storage", check_state_storage)


# ============================================================
print("\n" + "=" * 70)
print("PHASE 4: Utils and Paths Check")
print("=" * 70 + "\n")

def check_preset_manager():
    from utils.preset_manager import get_preset_manager, get_backtest_params
    pm = get_preset_manager()
    presets = pm.list_presets() if pm else []
    return {'presets': len(presets) if presets else 0}

def check_paths():
    from paths import Paths
    attrs = ['BASE', 'CACHE', 'CONFIG', 'LOGS']
    found = [a for a in attrs if hasattr(Paths, a)]
    return {'attrs': found, 'BASE': str(getattr(Paths, 'BASE', 'N/A'))[:50]}

def check_paths_exe_compat():
    """EXE compatible paths"""
    from paths import Paths
    has_internal = hasattr(Paths, 'INTERNAL_BASE')
    has_ensure = hasattr(Paths, 'ensure_all')
    return {'INTERNAL_BASE': has_internal, 'ensure_all': has_ensure}

check("4.1 utils.preset_manager", check_preset_manager)
check("4.2 paths.Paths", check_paths)
check("4.3 paths EXE compat", check_paths_exe_compat)


# ============================================================
print("\n" + "=" * 70)
print("PHASE 5: GUI Widget Check")
print("=" * 70 + "\n")

# PyQt5 init
try:
    from PyQt5.QtWidgets import QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication([])
    print("   PyQt5 initialized\n")
except Exception as e:
    print(f"   PyQt5 init failed: {e}\n")
    app = None

def check_backtest_widget():
    from backtest_widget import BacktestWidget
    w = BacktestWidget()
    return {
        'strategy': w.strategy is not None,
        'preset_combo': w.preset_combo.count(),
        'chk_4h': hasattr(w, 'chk_4h'),
        '_run_btn': hasattr(w, '_run_btn'),
    }

def check_optimization_widget():
    from optimization_widget import OptimizationWidget
    w = OptimizationWidget()
    return {
        'data_combo': w.data_combo.count(),
        'param_widgets': len(w.param_widgets),
        'direction_widget': hasattr(w, 'direction_widget'),
    }

def check_settings_widget():
    from settings_widget import SettingsWidget
    w = SettingsWidget()
    return {
        'telegram_card': hasattr(w, 'telegram_card'),
        'exchange_toggles': len(w.exchange_toggles),
    }

def check_trading_dashboard():
    from trading_dashboard import TradingDashboard
    w = TradingDashboard()
    return {
        'control_panel': w.control_panel is not None,
        'signals': hasattr(w, 'start_trading_clicked'),
    }

def check_staru_main():
    from staru_main import StarUWindow
    w = StarUWindow(user_tier='admin')
    tabs = [w.tabs.tabText(i) for i in range(w.tabs.count())]
    return {
        'tabs': w.tabs.count(),
        'tab_names': tabs[:3],
    }

if app:
    check("5.1 backtest_widget", check_backtest_widget)
    check("5.2 optimization_widget", check_optimization_widget)
    check("5.3 settings_widget", check_settings_widget)
    check("5.4 trading_dashboard", check_trading_dashboard)
    check("5.5 staru_main", check_staru_main)
else:
    results['fail'].append(("5.x GUI widgets", "PyQt5 init failed", ""))


# ============================================================
print("\n" + "=" * 70)
print("PHASE 6: Signal Connection Check")
print("=" * 70 + "\n")

def check_signals():
    from staru_main import StarUWindow
    w = StarUWindow(user_tier='admin')
    
    signals = {}
    signals['backtest_finished'] = hasattr(w.backtest_widget, 'backtest_finished')
    signals['settings_applied'] = hasattr(w.optimization_widget, 'settings_applied')
    signals['start_trading'] = hasattr(w.dashboard, 'start_trading_clicked')
    signals['go_to_tab'] = hasattr(w.dashboard, 'go_to_tab')
    
    connected = sum(1 for v in signals.values() if v)
    return {'signals': signals, 'connected': f"{connected}/{len(signals)}"}

if app:
    check("6.1 widget signals", check_signals)


# ============================================================
print("\n" + "=" * 70)
print("PHASE 7: Data Flow Check")
print("=" * 70 + "\n")

def check_cache_dir():
    from pathlib import Path
    from paths import Paths
    cache_dir = Path(Paths.CACHE)
    exists = cache_dir.exists()
    files = list(cache_dir.glob("*.parquet")) if exists else []
    return {'exists': exists, 'parquet_files': len(files)}

def check_preset_dir():
    from pathlib import Path
    from paths import Paths
    preset_dir = Path(Paths.CONFIG) / "presets"
    exists = preset_dir.exists()
    files = list(preset_dir.glob("*.json")) if exists else []
    return {'exists': exists, 'preset_files': len(files)}

def check_indicator_generator():
    try:
        from indicator_generator import IndicatorGenerator
        return {'location': 'root', 'class': True}
    except ImportError:
        try:
            from GUI.indicator_generator import IndicatorGenerator
            return {'location': 'GUI/', 'class': True}
        except ImportError:
            raise Exception("IndicatorGenerator not found")

check("7.1 cache directory", check_cache_dir)
check("7.2 preset directory", check_preset_dir)
check("7.3 indicator_generator", check_indicator_generator)


# ============================================================
print("\n" + "=" * 70)
print("PHASE 8: Core->Exchange->Storage Flow Check")
print("=" * 70 + "\n")

def check_core_to_exchange():
    """unified_bot -> exchange_manager connection"""
    import inspect
    from core.unified_bot import UnifiedBot
    source = inspect.getsourcefile(UnifiedBot)
    with open(source, 'r', encoding='utf-8') as f:
        content = f.read()
    has_exchange = 'exchange_manager' in content or 'get_exchange' in content
    has_storage = 'trade_storage' in content or 'state_storage' in content
    return {'->exchange': has_exchange, '->storage': has_storage}

def check_backtest_to_strategy():
    """backtest_widget -> strategy_core connection"""
    import inspect
    from backtest_widget import BacktestWidget
    source = inspect.getsourcefile(BacktestWidget)
    with open(source, 'r', encoding='utf-8') as f:
        content = f.read()
    has_strategy = 'AlphaX7Core' in content or 'strategy_core' in content
    has_preset = 'preset_manager' in content
    return {'->strategy': has_strategy, '->preset': has_preset}

def check_optimization_flow():
    """optimization_widget -> optimizer -> strategy connection"""
    import inspect
    from optimization_widget import OptimizationWidget
    source = inspect.getsourcefile(OptimizationWidget)
    with open(source, 'r', encoding='utf-8') as f:
        content = f.read()
    has_optimizer = 'BacktestOptimizer' in content or 'optimizer' in content
    has_strategy = 'AlphaX7Core' in content
    return {'->optimizer': has_optimizer, '->strategy': has_strategy}

check("8.1 unified_bot connections", check_core_to_exchange)
check("8.2 backtest_widget connections", check_backtest_to_strategy)
check("8.3 optimization_widget connections", check_optimization_flow)


# ============================================================
print("\n" + "=" * 70)
print("FINAL RESULTS")
print("=" * 70)

print(f"\n[PASS] {len(results['pass'])} items")
for name, detail in results['pass']:
    print(f"   + {name}")

if results['warn']:
    print(f"\n[WARN] {len(results['warn'])} items")
    for name, detail in results['warn']:
        print(f"   ? {name}: {detail}")

if results['fail']:
    print(f"\n[FAIL] {len(results['fail'])} items")
    for item in results['fail']:
        name = item[0]
        error = item[1] if len(item) > 1 else "Unknown"
        print(f"   X {name}")
        print(f"     -> {error}")

print("\n" + "=" * 70)
total = len(results['pass']) + len(results['warn']) + len(results['fail'])
pass_rate = len(results['pass']) / total * 100 if total > 0 else 0

if results['fail']:
    print(f"RESULT: {pass_rate:.0f}% - FIX REQUIRED!")
elif results['warn']:
    print(f"RESULT: {pass_rate:.0f}% - WARN check recommended")
else:
    print(f"RESULT: {pass_rate:.0f}% - EXE BUILD READY!")
print("=" * 70)

# Detail for failed items
if results['fail']:
    print("\n" + "=" * 70)
    print("FAIL DETAILS (fix required)")
    print("=" * 70)
    for item in results['fail']:
        name = item[0]
        error = item[1] if len(item) > 1 else "Unknown"
        trace = item[2] if len(item) > 2 else ""
        print(f"\n[{name}]")
        print(f"Error: {error}")
        if trace:
            print("Traceback:")
            print(trace[:500])
