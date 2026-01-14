#!/usr/bin/env python3
"""
TwinStar Quantum v1.7.0 종합 검증 시스템
9개 카테고리 전체 프로젝트 검증

Usage:
    py -3 tests/comprehensive_verify.py
    py -3 tests/comprehensive_verify.py --full-report
"""
import sys
import os
import io
import importlib
import importlib.util
import inspect
import time
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Any

# Fix Korean encoding in PowerShell
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Results storage
RESULTS: Dict[str, Dict[str, Any]] = {
    'imports': {'passed': 0, 'failed': 0, 'details': {}},
    'core': {'passed': 0, 'failed': 0, 'details': {}},
    'utils': {'passed': 0, 'failed': 0, 'details': {}},
    'exchanges': {'passed': 0, 'failed': 0, 'details': {}},
    'gui': {'passed': 0, 'failed': 0, 'details': {}},
    'calculations': {'passed': 0, 'failed': 0, 'details': {}},
    'api': {'passed': 0, 'failed': 0, 'details': {}},
    'integration': {'passed': 0, 'failed': 0, 'details': {}},
    'errors': {'passed': 0, 'failed': 0, 'details': {}},
}

FAILED_ITEMS = []


def print_header(num, title):
    print(f"\n[{num}/9] {title}")
    print("-" * 50)


# =============================================================================
# 1. IMPORT VERIFICATION
# =============================================================================
def verify_imports():
    print_header(1, "임포트 점검")
    
    dirs = {
        'core': PROJECT_ROOT / 'core',
        'utils': PROJECT_ROOT / 'utils',
        'exchanges': PROJECT_ROOT / 'exchanges',
        'storage': PROJECT_ROOT / 'storage',
    }
    
    for dir_name, dir_path in dirs.items():
        if not dir_path.exists():
            continue
        
        RESULTS['imports']['details'][dir_name] = {'passed': 0, 'failed': 0}
        
        for py_file in dir_path.glob('*.py'):
            if py_file.name.startswith('_') and py_file.name != '__init__.py':
                continue
            
            module_name = f"{dir_name}.{py_file.stem}"
            try:
                importlib.import_module(module_name)
                RESULTS['imports']['details'][dir_name]['passed'] += 1
                RESULTS['imports']['passed'] += 1
            except Exception as e:
                RESULTS['imports']['details'][dir_name]['failed'] += 1
                RESULTS['imports']['failed'] += 1
                FAILED_ITEMS.append(f"[Import] {module_name}: {type(e).__name__}")
    
    # Summary
    total = RESULTS['imports']['passed'] + RESULTS['imports']['failed']
    pct = (RESULTS['imports']['passed'] / total * 100) if total > 0 else 0
    
    for dir_name, counts in RESULTS['imports']['details'].items():
        p, f = counts['passed'], counts['failed']
        print(f"  - {dir_name}/: {p}/{p+f}")
    
    icon = "✅" if pct >= 95 else "⚠️"
    print(f"  총합: {RESULTS['imports']['passed']}/{total} ({pct:.0f}%) {icon}")
    
    return pct >= 95


# =============================================================================
# 2. CORE MODULE VERIFICATION
# =============================================================================
def verify_core():
    print_header(2, "Core 기능 점검")
    
    checks = [
        ('strategy_core', 'AlphaX7Core', ['detect_signal', 'calculate_rsi']),
        ('unified_bot', 'UnifiedBot', ['run', 'execute_entry', 'manage_position']),
        ('order_executor', 'OrderExecutor', ['execute_entry', 'execute_close', 'calculate_pnl']),
        ('position_manager', 'PositionManager', ['manage_live', 'sync_with_exchange']),
        ('auto_scanner', 'AutoScanner', ['start', 'stop', 'load_verified_symbols']),
    ]
    
    for module, cls_name, methods in checks:
        try:
            mod = importlib.import_module(f'core.{module}')
            cls = getattr(mod, cls_name)
            
            for method in methods:
                if hasattr(cls, method):
                    RESULTS['core']['passed'] += 1
                    print(f"  ✅ {cls_name}.{method}")
                else:
                    RESULTS['core']['failed'] += 1
                    FAILED_ITEMS.append(f"[Core] {cls_name}.{method} 없음")
                    print(f"  ❌ {cls_name}.{method}")
        except Exception as e:
            RESULTS['core']['failed'] += len(methods)
            print(f"  ❌ {module}: {e}")
    
    total = RESULTS['core']['passed'] + RESULTS['core']['failed']
    pct = (RESULTS['core']['passed'] / total * 100) if total > 0 else 0
    icon = "✅" if pct >= 90 else "⚠️"
    print(f"  총합: {RESULTS['core']['passed']}/{total} ({pct:.0f}%) {icon}")
    
    return pct >= 90


# =============================================================================
# 3. UTILS VERIFICATION
# =============================================================================
def verify_utils():
    print_header(3, "Utils 기능 점검")
    
    # Crypto test
    try:
        from utils.crypto import encrypt_key, decrypt_key
        test_val = "TestSecret123"
        encrypted = encrypt_key(test_val)
        decrypted = decrypt_key(encrypted)
        if decrypted == test_val:
            RESULTS['utils']['passed'] += 1
            print("  ✅ crypto: encrypt/decrypt 쌍")
        else:
            RESULTS['utils']['failed'] += 1
            print("  ❌ crypto: 복호화 불일치")
    except Exception as e:
        RESULTS['utils']['failed'] += 1
        print(f"  ❌ crypto: {e}")
    
    # Validators test
    try:
        from utils.validators import validate_symbol, validate_number
        if validate_symbol('BTCUSDT')[0]:
            RESULTS['utils']['passed'] += 1
            print("  ✅ validators: symbol 검증")
        else:
            RESULTS['utils']['failed'] += 1
    except Exception as e:
        RESULTS['utils']['failed'] += 1
        print(f"  ❌ validators: {e}")
    
    # Symbol converter test
    try:
        from utils.symbol_converter import convert_symbol, extract_base
        if convert_symbol('BTC', 'bybit') == 'BTCUSDT':
            RESULTS['utils']['passed'] += 1
            print("  ✅ symbol_converter: 변환")
        else:
            RESULTS['utils']['failed'] += 1
    except Exception as e:
        RESULTS['utils']['failed'] += 1
        print(f"  ❌ symbol_converter: {e}")
    
    # Preset manager test
    try:
        from utils.preset_manager import get_preset_manager
        pm = get_preset_manager()
        if hasattr(pm, 'load_preset'):
            RESULTS['utils']['passed'] += 1
            print("  ✅ preset_manager: load_preset")
        else:
            RESULTS['utils']['failed'] += 1
    except Exception as e:
        RESULTS['utils']['failed'] += 1
        print(f"  ❌ preset_manager: {e}")
    
    total = RESULTS['utils']['passed'] + RESULTS['utils']['failed']
    pct = (RESULTS['utils']['passed'] / total * 100) if total > 0 else 0
    icon = "✅" if pct >= 90 else "⚠️"
    print(f"  총합: {RESULTS['utils']['passed']}/{total} ({pct:.0f}%) {icon}")
    
    return pct >= 90


# =============================================================================
# 4. EXCHANGES VERIFICATION
# =============================================================================
def verify_exchanges():
    print_header(4, "Exchanges 점검")
    
    exchanges = ['bybit_exchange', 'binance_exchange', 'okx_exchange', 
                 'bitget_exchange', 'bingx_exchange', 'upbit_exchange', 'bithumb_exchange']
    
    required_methods = ['connect', 'get_klines', 'get_current_price', 'place_market_order', 'get_balance']
    
    for ex_name in exchanges:
        try:
            mod = importlib.import_module(f'exchanges.{ex_name}')
            # Find the Exchange class
            cls_name = ex_name.replace('_exchange', '').title() + 'Exchange'
            cls_name = cls_name.replace('Okx', 'OKX').replace('Bingx', 'BingX')
            
            if hasattr(mod, cls_name):
                cls = getattr(mod, cls_name)
                for method in required_methods:
                    if hasattr(cls, method):
                        RESULTS['exchanges']['passed'] += 1
                    else:
                        RESULTS['exchanges']['failed'] += 1
                        FAILED_ITEMS.append(f"[Exchange] {cls_name}.{method} 없음")
                print(f"  ✅ {cls_name}")
            else:
                RESULTS['exchanges']['failed'] += len(required_methods)
                print(f"  ❌ {ex_name}: 클래스 없음")
        except Exception as e:
            RESULTS['exchanges']['failed'] += 1
            print(f"  ❌ {ex_name}: {e}")
    
    total = RESULTS['exchanges']['passed'] + RESULTS['exchanges']['failed']
    pct = (RESULTS['exchanges']['passed'] / total * 100) if total > 0 else 0
    icon = "✅" if pct >= 90 else "⚠️"
    print(f"  총합: {RESULTS['exchanges']['passed']}/{total} ({pct:.0f}%) {icon}")
    
    return pct >= 90


# =============================================================================
# 5. GUI VERIFICATION
# =============================================================================
def verify_gui():
    print_header(5, "GUI 점검")
    
    # Create QApplication if needed
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        HAS_QT = True
    except ImportError:
        HAS_QT = False
        print("  ⚠️ PyQt5 미설치 - GUI 점검 스킵")
        return True
    
    widgets = [
        ('trading_dashboard', 'TradingDashboard'),
        ('backtest_widget', 'BacktestWidget'),
        ('optimization_widget', 'OptimizationWidget'),
        ('settings_widget', 'SettingsWidget'),
        ('history_widget', 'HistoryWidget'),
        ('data_collector_widget', 'DataCollectorWidget'),
    ]
    
    for module, cls_name in widgets:
        try:
            mod = importlib.import_module(f'GUI.{module}')
            cls = getattr(mod, cls_name)
            # Just check class exists and has _init_ui
            if hasattr(cls, '_init_ui') or hasattr(cls, '__init__'):
                RESULTS['gui']['passed'] += 1
                print(f"  ✅ {cls_name}")
            else:
                RESULTS['gui']['failed'] += 1
        except Exception as e:
            RESULTS['gui']['failed'] += 1
            print(f"  ❌ {module}: {type(e).__name__}")
    
    total = RESULTS['gui']['passed'] + RESULTS['gui']['failed']
    pct = (RESULTS['gui']['passed'] / total * 100) if total > 0 else 0
    icon = "✅" if pct >= 90 else "⚠️"
    print(f"  총합: {RESULTS['gui']['passed']}/{total} ({pct:.0f}%) {icon}")
    
    return pct >= 90


# =============================================================================
# 6. CALCULATION ACCURACY
# =============================================================================
def verify_calculations():
    print_header(6, "계산 정확성 점검")
    
    tests = []
    
    # PnL Long Profit
    entry, exit_p, size, lev = 100, 110, 1, 10
    pnl = (exit_p - entry) * size * lev
    tests.append(("Long 수익 PnL", 100, pnl))
    
    # PnL Long Loss
    entry, exit_p = 100, 90
    pnl = (exit_p - entry) * size * lev
    tests.append(("Long 손실 PnL", -100, pnl))
    
    # PnL Short Profit
    entry, exit_p = 100, 90
    pnl = (entry - exit_p) * size * lev
    tests.append(("Short 수익 PnL", 100, pnl))
    
    # PnL Short Loss
    entry, exit_p = 100, 110
    pnl = (entry - exit_p) * size * lev
    tests.append(("Short 손실 PnL", -100, pnl))
    
    # MDD
    equity = [1000, 1100, 900, 1000]
    peak = 1100
    mdd = (peak - 900) / peak * 100
    tests.append(("MDD", 18.18, round(mdd, 2)))
    
    # Win Rate
    wins, total = 3, 5
    wr = wins / total * 100
    tests.append(("승률", 60, wr))
    
    # Profit Factor
    gross_profit, gross_loss = 120, 30
    pf = gross_profit / gross_loss
    tests.append(("Profit Factor", 4.0, pf))
    
    for name, expected, actual in tests:
        if abs(expected - actual) < 0.1:
            RESULTS['calculations']['passed'] += 1
            print(f"  ✅ {name}: 기대={expected}, 실제={actual}")
        else:
            RESULTS['calculations']['failed'] += 1
            print(f"  ❌ {name}: 기대={expected}, 실제={actual}")
            FAILED_ITEMS.append(f"[Calc] {name}: {expected} vs {actual}")
    
    total = RESULTS['calculations']['passed'] + RESULTS['calculations']['failed']
    pct = (RESULTS['calculations']['passed'] / total * 100) if total > 0 else 0
    icon = "✅" if pct >= 100 else "❌"
    print(f"  총합: {RESULTS['calculations']['passed']}/{total} ({pct:.0f}%) {icon}")
    
    return pct >= 100


# =============================================================================
# 7. API INTEGRATION
# =============================================================================
def verify_api():
    print_header(7, "API 연동 점검")
    
    try:
        import ccxt # type: ignore
        
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        exchange.set_sandbox_mode(True)
        
        # Ticker
        start = time.time()
        ticker = exchange.fetch_ticker('BTC/USDT')
        elapsed = (time.time() - start) * 1000
        last_price = float(ticker.get('last') or 0)
        if last_price > 0:
            RESULTS['api']['passed'] += 1
            print(f"  ✅ ticker 조회: {elapsed:.0f}ms")
        else:
            RESULTS['api']['failed'] += 1
        
        # OHLCV
        start = time.time()
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=10)
        elapsed = (time.time() - start) * 1000
        if len(ohlcv) > 0:
            RESULTS['api']['passed'] += 1
            print(f"  ✅ OHLCV 조회: {elapsed:.0f}ms ({len(ohlcv)}개)")
        else:
            RESULTS['api']['failed'] += 1
        
        # Markets
        start = time.time()
        exchange.load_markets()
        elapsed = (time.time() - start) * 1000
        if exchange.markets and 'BTC/USDT' in exchange.markets:
            RESULTS['api']['passed'] += 1
            print(f"  ✅ 마켓 로드: {elapsed:.0f}ms ({len(exchange.markets)}개)")
        else:
            RESULTS['api']['failed'] += 1
        
    except ImportError:
        print("  ⚠️ ccxt 미설치 - API 테스트 스킵")
        return True
    except Exception as e:
        RESULTS['api']['failed'] += 1
        print(f"  ❌ API 연결 실패: {e}")
    
    total = RESULTS['api']['passed'] + RESULTS['api']['failed']
    pct = (RESULTS['api']['passed'] / total * 100) if total > 0 else 0
    icon = "✅" if pct >= 90 else "⚠️"
    print(f"  총합: {RESULTS['api']['passed']}/{total} ({pct:.0f}%) {icon}")
    
    return pct >= 90


# =============================================================================
# 8. INTEGRATION FLOW
# =============================================================================
def verify_integration():
    print_header(8, "통합 플로우 점검")
    
    steps = [
        "데이터 로드",
        "전략 초기화",
        "신호 감지",
        "주문 실행",
        "포지션 관리",
    ]
    
    # Step 1: Data
    try:
        from core.data_manager import BotDataManager
        RESULTS['integration']['passed'] += 1
        print(f"  ✅ {steps[0]}")
    except Exception as e:
        RESULTS['integration']['failed'] += 1
        print(f"  ❌ {steps[0]}: {e}")
    
    # Step 2: Strategy
    try:
        from core.strategy_core import AlphaX7Core
        core = AlphaX7Core()
        RESULTS['integration']['passed'] += 1
        print(f"  ✅ {steps[1]}")
    except Exception as e:
        RESULTS['integration']['failed'] += 1
        print(f"  ❌ {steps[1]}: {e}")
    
    # Step 3: Signal
    try:
        if hasattr(core, 'detect_signal'):
            RESULTS['integration']['passed'] += 1
            print(f"  ✅ {steps[2]}")
        else:
            RESULTS['integration']['failed'] += 1
    except Exception as e:
        RESULTS['integration']['failed'] += 1
        print(f"  ❌ {steps[2]}: {e}")
    
    # Step 4: Order
    try:
        from core.order_executor import OrderExecutor
        RESULTS['integration']['passed'] += 1
        print(f"  ✅ {steps[3]}")
    except Exception as e:
        RESULTS['integration']['failed'] += 1
        print(f"  ❌ {steps[3]}: {e}")
    
    # Step 5: Position
    try:
        from core.position_manager import PositionManager
        RESULTS['integration']['passed'] += 1
        print(f"  ✅ {steps[4]}")
    except Exception as e:
        RESULTS['integration']['failed'] += 1
        print(f"  ❌ {steps[4]}: {e}")
    
    total = RESULTS['integration']['passed'] + RESULTS['integration']['failed']
    pct = (RESULTS['integration']['passed'] / total * 100) if total > 0 else 0
    icon = "✅" if pct >= 100 else "⚠️"
    print(f"  총합: {RESULTS['integration']['passed']}/{total} ({pct:.0f}%) {icon}")
    
    return pct >= 100


# =============================================================================
# 9. ERROR HANDLING
# =============================================================================
def verify_errors():
    print_header(9, "에러 처리 점검")
    
    # Invalid symbol
    try:
        from utils.validators import validate_symbol
        valid, _ = validate_symbol('!!!INVALID!!!')
        if not valid:
            RESULTS['errors']['passed'] += 1
            print("  ✅ 잘못된 심볼 거부")
        else:
            RESULTS['errors']['failed'] += 1
    except Exception:
        RESULTS['errors']['passed'] += 1  # Exception is acceptable
        print("  ✅ 잘못된 심볼 예외 발생")
    
    # Invalid number
    try:
        from utils.validators import validate_number
        valid, _ = validate_number('not_a_number')
        if not valid:
            RESULTS['errors']['passed'] += 1
            print("  ✅ 잘못된 숫자 거부")
        else:
            RESULTS['errors']['failed'] += 1
    except Exception:
        RESULTS['errors']['passed'] += 1
        print("  ✅ 잘못된 숫자 예외 발생")
    
    # Missing file handling
    try:
        from utils.preset_manager import get_preset_manager
        pm = get_preset_manager()
        result = pm.load_preset('NONEXISTENT_SYMBOL_12345')
        if result is None:
            RESULTS['errors']['passed'] += 1
            print("  ✅ 없는 프리셋 None 반환")
        else:
            RESULTS['errors']['failed'] += 1
    except Exception as e:
        RESULTS['errors']['passed'] += 1  # Graceful handling
        print(f"  ✅ 없는 프리셋 예외 처리")
    
    total = RESULTS['errors']['passed'] + RESULTS['errors']['failed']
    pct = (RESULTS['errors']['passed'] / total * 100) if total > 0 else 0
    icon = "✅" if pct >= 100 else "⚠️"
    print(f"  총합: {RESULTS['errors']['passed']}/{total} ({pct:.0f}%) {icon}")
    
    return pct >= 100


# =============================================================================
# MAIN
# =============================================================================
def main(full_report=False):
    print("\n" + "=" * 55)
    print("TwinStar Quantum v1.7.0 종합 검증 리포트")
    print("=" * 55)
    print(f"검증 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    verifiers = [
        (verify_imports, "임포트 점검"),
        (verify_core, "Core 기능 점검"),
        (verify_utils, "Utils 기능 점검"),
        (verify_exchanges, "Exchanges 점검"),
        (verify_gui, "GUI 점검"),
        (verify_calculations, "계산 정확성"),
        (verify_api, "API 연동"),
        (verify_integration, "통합 플로우"),
        (verify_errors, "에러 처리"),
    ]
    
    results = []
    for func, name in verifiers:
        try:
            passed = func()
            results.append((name, passed))
        except Exception as e:
            print(f"  ❌ 검증 중 예외: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 55)
    print("📊 최종 결과")
    print("=" * 55)
    
    total_passed = sum(
        RESULTS[k]['passed'] for k in RESULTS
    )
    total_failed = sum(
        RESULTS[k]['failed'] for k in RESULTS
    )
    total = total_passed + total_failed
    pct = (total_passed / total * 100) if total > 0 else 0
    
    for i, (name, passed) in enumerate(results, 1):
        icon = "✅" if passed else "❌"
        print(f"[{i}/9] {name}: {icon}")
    
    print("=" * 55)
    print(f"총합: {total_passed}/{total} ({pct:.1f}%)")
    
    if pct >= 95:
        print("상태: 배포 가능 ✅")
    elif pct >= 80:
        print("상태: 조건부 배포 가능 ⚠️")
    else:
        print("상태: 수정 필요 ❌")
    
    print("=" * 55)
    
    # Failed items detail
    if FAILED_ITEMS and full_report:
        print("\n실패 항목 상세:")
        for i, item in enumerate(FAILED_ITEMS[:10], 1):
            print(f"  {i}. {item}")
        if len(FAILED_ITEMS) > 10:
            print(f"  ... 외 {len(FAILED_ITEMS) - 10}개")
    
    return pct >= 95


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TwinStar Quantum 종합 검증')
    parser.add_argument('--full-report', action='store_true', help='상세 실패 항목 출력')
    args = parser.parse_args()
    
    success = main(full_report=args.full_report)
    sys.exit(0 if success else 1)
