"""
런타임 통합 테스트
타입 체크는 통과했지만 실제 동작 여부 검증
"""
import sys
import importlib
from typing import List, Tuple

def test_core_imports() -> Tuple[int, int, List[str]]:
    """핵심 모듈 import 테스트"""
    print("\n=== Core Module Import Test ===")

    modules = [
        'config.constants',
        'config.parameters',
        'utils.logger',
        'utils.indicators',
        'utils.formatters.datetime',
        'utils.formatters.numbers',
    ]

    success = 0
    failed = 0
    errors = []

    for module in modules:
        try:
            importlib.import_module(module)
            print(f"[OK] {module}")
            success += 1
        except Exception as e:
            msg = f"[FAIL] {module}: {str(e)[:60]}"
            print(msg)
            errors.append(msg)
            failed += 1

    return success, failed, errors


def test_class_imports() -> Tuple[int, int, List[str]]:
    """주요 클래스 import 테스트"""
    print("\n=== Class Import Test ===")

    classes = [
        ('core.unified_bot', 'UnifiedBot'),
        ('core.strategy_core', 'AlphaX7Core'),
        ('exchanges.base_exchange', 'BaseExchange'),
        ('exchanges.binance_exchange', 'BinanceExchange'),
        ('strategies.base_strategy', 'BaseStrategy'),
    ]

    success = 0
    failed = 0
    errors = []

    for module_path, class_name in classes:
        try:
            mod = importlib.import_module(module_path)
            cls = getattr(mod, class_name)
            print(f"[OK] {module_path}.{class_name}")
            success += 1
        except Exception as e:
            msg = f"[FAIL] {module_path}.{class_name}: {str(e)[:60]}"
            print(msg)
            errors.append(msg)
            failed += 1

    return success, failed, errors


def test_config_values() -> Tuple[int, int, List[str]]:
    """설정 값 검증"""
    print("\n=== Config Values Test ===")

    success = 0
    failed = 0
    errors = []

    try:
        from config.constants import EXCHANGE_INFO, TF_MAPPING
        from config.parameters import DEFAULT_PARAMS

        # EXCHANGE_INFO 검증
        if len(EXCHANGE_INFO) > 0:
            print(f"[OK] EXCHANGE_INFO: {len(EXCHANGE_INFO)} exchanges")
            success += 1
        else:
            msg = "[FAIL] EXCHANGE_INFO is empty"
            print(msg)
            errors.append(msg)
            failed += 1

        # TF_MAPPING 검증
        if len(TF_MAPPING) > 0:
            print(f"[OK] TF_MAPPING: {len(TF_MAPPING)} timeframes")
            success += 1
        else:
            msg = "[FAIL] TF_MAPPING is empty"
            print(msg)
            errors.append(msg)
            failed += 1

        # DEFAULT_PARAMS 검증
        if len(DEFAULT_PARAMS) > 0:
            print(f"[OK] DEFAULT_PARAMS: {len(DEFAULT_PARAMS)} parameters")
            success += 1
        else:
            msg = "[FAIL] DEFAULT_PARAMS is empty"
            print(msg)
            errors.append(msg)
            failed += 1

    except Exception as e:
        msg = f"[FAIL] Config import: {str(e)}"
        print(msg)
        errors.append(msg)
        failed += 1

    return success, failed, errors


def test_indicator_functions() -> Tuple[int, int, List[str]]:
    """지표 함수 실행 테스트"""
    print("\n=== Indicator Function Test ===")

    success = 0
    failed = 0
    errors = []

    try:
        import pandas as pd
        import numpy as np
        from utils.indicators import calculate_rsi, calculate_atr

        # 테스트 데이터 생성
        data = {
            'close': np.random.uniform(100, 200, 100),
            'high': np.random.uniform(150, 250, 100),
            'low': np.random.uniform(50, 150, 100),
        }
        df = pd.DataFrame(data)

        # RSI 계산 테스트 (return_series=True 전달)
        try:
            rsi = calculate_rsi(df['close'], return_series=True)
            if isinstance(rsi, pd.Series) and len(rsi) == len(df):
                print(f"[OK] calculate_rsi: {len(rsi)} values")
                success += 1
            else:
                msg = f"[FAIL] calculate_rsi: not a Series or length mismatch"
                print(msg)
                errors.append(msg)
                failed += 1
        except Exception as e:
            msg = f"[FAIL] calculate_rsi: {str(e)[:60]}"
            print(msg)
            errors.append(msg)
            failed += 1

        # ATR 계산 테스트 (return_series=True 전달)
        try:
            atr = calculate_atr(df, return_series=True)
            if isinstance(atr, pd.Series) and len(atr) == len(df):
                print(f"[OK] calculate_atr: {len(atr)} values")
                success += 1
            else:
                msg = f"[FAIL] calculate_atr: not a Series or length mismatch"
                print(msg)
                errors.append(msg)
                failed += 1
        except Exception as e:
            msg = f"[FAIL] calculate_atr: {str(e)[:60]}"
            print(msg)
            errors.append(msg)
            failed += 1

    except Exception as e:
        msg = f"[FAIL] Indicator test setup: {str(e)}"
        print(msg)
        errors.append(msg)
        failed += 1

    return success, failed, errors


def main():
    """전체 테스트 실행"""
    print("=" * 60)
    print("TwinStar-Quantum Runtime Test")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Path: {sys.executable}")

    total_success = 0
    total_failed = 0
    all_errors = []

    # 테스트 실행
    tests = [
        ("Core Imports", test_core_imports),
        ("Class Imports", test_class_imports),
        ("Config Values", test_config_values),
        ("Indicator Functions", test_indicator_functions),
    ]

    for test_name, test_func in tests:
        try:
            success, failed, errors = test_func()
            total_success += success
            total_failed += failed
            all_errors.extend(errors)
        except Exception as e:
            print(f"\n[ERROR] {test_name} crashed: {e}")
            total_failed += 1
            all_errors.append(f"{test_name}: {str(e)}")

    # 결과 요약
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    print(f"Success: {total_success}")
    print(f"Failed:  {total_failed}")
    print(f"Total:   {total_success + total_failed}")

    if total_failed > 0:
        print("\nFailed Tests:")
        for error in all_errors:
            print(f"  - {error}")
        print("\n[RESULT] FAILED - Some tests did not pass")
        return 1
    else:
        print("\n[RESULT] SUCCESS - All tests passed!")
        return 0


if __name__ == '__main__':
    sys.exit(main())
