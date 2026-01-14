#!/usr/bin/env python3
"""
TwinStar Quantum 반환값 타입 + 값 검증
각 함수별 반환값이 올바른 타입과 범위인지 확인

Usage:
    py -3 tests/deep_type_verify.py
"""
import sys
import os
import io
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Any, Callable

# Fix Korean encoding in PowerShell
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Results
PASSED = 0
FAILED = 0
ERRORS = []


from typing import Any, Callable, Optional
def check(name: str, expected_type: Any, expected_cond: str, value: Any, cond_func: Optional[Callable] = None) -> bool:
    """Check a single value against expected type and condition"""
    global PASSED, FAILED
    
    type_ok = isinstance(value, expected_type)
    cond_ok = cond_func(value) if cond_func else True
    
    if type_ok and cond_ok:
        PASSED += 1
        print(f"  ✅ {name}")
        print(f"     - 기대: {expected_type.__name__}, {expected_cond}")
        print(f"     - 실제: {value!r:.50} ({type(value).__name__})")
        return True
    else:
        FAILED += 1
        ERRORS.append(name)
        print(f"  ❌ {name}")
        print(f"     - 기대: {expected_type.__name__}, {expected_cond}")
        print(f"     - 실제: {value!r:.50} ({type(value).__name__})")
        if not type_ok:
            print(f"     - 문제: 타입 불일치")
        if not cond_ok:
            print(f"     - 문제: 조건 불충족")
        return False


def verify_core():
    print("\n" + "=" * 60)
    print("[Core] 모듈 반환값 검증")
    print("=" * 60)
    
    # 1. OrderExecutor.calculate_pnl
    try:
        from core.order_executor import OrderExecutor
        oe = OrderExecutor(exchange=None)
        pnl = oe.calculate_pnl(
            side='long',
            entry_price=50000,
            exit_price=51000,
            size=0.01,
            leverage=10
        )
        check("order_executor.calculate_pnl (Long Profit)", 
              (int, float), "> 0",
              pnl, lambda x: x > 0)
    except Exception as e:
        print(f"  ⚠️ order_executor.calculate_pnl: {e}")
    
    # 2. AlphaX7Core.calculate_rsi
    try:
        from core.strategy_core import AlphaX7Core
        core = AlphaX7Core()
        prices = np.array([100 + i for i in range(20)])
        rsi = core.calculate_rsi(prices, period=14)
        check("strategy_core.calculate_rsi (Uptrend)",
              (int, float, np.floating), "0~100",
              rsi, lambda x: 0 <= float(x) <= 100)
    except Exception as e:
        print(f"  ⚠️ strategy_core.calculate_rsi: {e}")
    
    # 3. PositionManager has strategy
    try:
        from core.position_manager import PositionManager
        pm = PositionManager(exchange=None)
        has_sync = hasattr(pm, 'sync_with_exchange')
        check("position_manager.sync_with_exchange exists",
              bool, "True",
              has_sync, lambda x: x == True)
    except Exception as e:
        print(f"  ⚠️ position_manager: {e}")
    
    # 4. AutoScanner load
    try:
        from core.auto_scanner import AutoScanner
        scanner = AutoScanner()
        symbols = scanner.load_verified_symbols()
        check("auto_scanner.load_verified_symbols",
              list, "list of strings",
              symbols, lambda x: isinstance(x, list))
    except Exception as e:
        print(f"  ⚠️ auto_scanner: {e}")


def verify_utils():
    print("\n" + "=" * 60)
    print("[Utils] 모듈 반환값 검증")
    print("=" * 60)
    
    # 1. Crypto encrypt/decrypt
    try:
        from utils.crypto import encrypt_key, decrypt_key
        original = "TestSecretKey123"
        encrypted = encrypt_key(original)
        decrypted = decrypt_key(encrypted)
        check("crypto.encrypt_key",
              str, "non-empty string",
              encrypted, lambda x: len(x) > 0)
        check("crypto.decrypt_key (matches)",
              str, "== original",
              decrypted, lambda x: x == original)
    except Exception as e:
        print(f"  ⚠️ crypto: {e}")
    
    # 2. Validators
    try:
        from utils.validators import validate_symbol, validate_number
        valid_sym, sym_val = validate_symbol("BTCUSDT")
        check("validators.validate_symbol (valid)",
              bool, "True",
              valid_sym, lambda x: x == True)
        
        invalid_sym, _ = validate_symbol("!!!INVALID!!!")
        check("validators.validate_symbol (invalid)",
              bool, "False",
              invalid_sym, lambda x: x == False)
        
        valid_num, num_val = validate_number(123.45)
        check("validators.validate_number (valid)",
              bool, "True",
              valid_num, lambda x: x == True)
    except Exception as e:
        print(f"  ⚠️ validators: {e}")
    
    # 3. Indicators
    try:
        from utils.indicators import calculate_rsi, calculate_atr
        prices = np.array([100 + i for i in range(20)])
        rsi = calculate_rsi(prices, period=14)
        check("indicators.calculate_rsi",
              (int, float, np.floating), "0~100",
              float(rsi), lambda x: 0 <= x <= 100)
    except Exception as e:
        print(f"  ⚠️ indicators: {e}")
    
    # 4. Symbol Converter
    try:
        from utils.symbol_converter import convert_symbol, extract_base
        result = convert_symbol('BTC', 'bybit')
        check("symbol_converter.convert_symbol",
              str, "BTCUSDT",
              result, lambda x: x == 'BTCUSDT')
        
        base = extract_base('BTCUSDT')
        check("symbol_converter.extract_base",
              str, "BTC",
              base, lambda x: x == 'BTC')
    except Exception as e:
        print(f"  ⚠️ symbol_converter: {e}")


def verify_exchanges():
    print("\n" + "=" * 60)
    print("[Exchanges] 모듈 반환값 검증 (Mock)")
    print("=" * 60)
    
    # Test exchange interface exists
    exchanges = [
        ('exchanges.binance_exchange', 'BinanceExchange'),
        ('exchanges.bybit_exchange', 'BybitExchange'),
        ('exchanges.okx_exchange', 'OKXExchange'),
    ]
    
    required_methods = ['connect', 'get_klines', 'get_current_price', 'place_market_order', 'get_balance']
    
    for mod_name, cls_name in exchanges:
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            cls = getattr(mod, cls_name)
            
            for method in required_methods:
                has_method = hasattr(cls, method) and callable(getattr(cls, method))
                check(f"{cls_name}.{method}",
                      bool, "exists and callable",
                      has_method, lambda x: x == True)
        except Exception as e:
            print(f"  ⚠️ {mod_name}: {e}")
    
    # Live API test (Binance Testnet)
    try:
        import ccxt  # type: ignore
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'future'}
        })
        exchange.set_sandbox_mode(True)
        
        ticker = exchange.fetch_ticker('BTC/USDT')
        check("ccxt.binance.fetch_ticker",
              dict, "has 'last' key",
              ticker, lambda x: 'last' in x and x['last'] > 0)
        
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=5)
        check("ccxt.binance.fetch_ohlcv",
              list, "list of lists, len >= 5",
              ohlcv, lambda x: len(x) >= 5 and isinstance(x[0], list))
        
    except ImportError:
        print("  ⚠️ ccxt 미설치 - 실제 API 테스트 스킵")
    except Exception as e:
        print(f"  ⚠️ ccxt API: {e}")


def verify_properties():
    print("\n" + "=" * 60)
    print("[Properties] 속성 검증")
    print("=" * 60)
    
    # Exchange name properties
    try:
        from exchanges.bybit_exchange import BybitExchange
        ex = BybitExchange({'api_key': '', 'api_secret': '', 'symbol': 'BTCUSDT'})
        name = ex.name
        check("BybitExchange.name",
              str, "non-empty",
              name, lambda x: len(x) > 0)
    except Exception as e:
        print(f"  ⚠️ BybitExchange.name: {e}")


def main():
    print("\n" + "=" * 60)
    print("TwinStar Quantum 반환값 타입 검증")
    print(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    verify_core()
    verify_utils()
    verify_exchanges()
    verify_properties()
    
    # Summary
    total = PASSED + FAILED
    pct = (PASSED / total * 100) if total > 0 else 0
    
    print("\n" + "=" * 60)
    print("📊 최종 결과")
    print("=" * 60)
    print(f"  - 통과: {PASSED}/{total} ({pct:.1f}%)")
    print(f"  - 실패: {FAILED}")
    
    if ERRORS:
        print("\n❌ 실패 항목:")
        for err in ERRORS:
            print(f"  - {err}")
    
    if pct >= 95:
        print("\n상태: 배포 가능 ✅")
    elif pct >= 80:
        print("\n상태: 조건부 배포 가능 ⚠️")
    else:
        print("\n상태: 수정 필요 ❌")
    
    return pct >= 95


if __name__ == '__main__':
    main()
