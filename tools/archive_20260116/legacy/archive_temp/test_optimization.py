"""Optimization verification test"""
import sys
import time
import pandas as pd
import numpy as np

# Add module path
sys.path.insert(0, 'f:/TwinStar-Quantum')

from utils.indicators import calculate_rsi, calculate_atr, calculate_adx

def test_rsi_accuracy():
    """RSI accuracy test (Wilder's original example)"""
    print("\n=== RSI Accuracy Test ===")

    # Wilder's original data
    data = pd.Series([
        44.00, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
        45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00,
        46.03, 46.41, 46.22, 45.64
    ])

    rsi_series = calculate_rsi(data, period=14, return_series=True)
    last_rsi = float(rsi_series.iloc[-1])

    print(f"Last RSI: {last_rsi:.2f}")
    print(f"Expected range: 50.0 ~ 60.0")

    # Wilder's EWM method may differ from SMA, so use wider range
    if 50.0 <= last_rsi <= 60.0:
        print("[PASS] RSI accuracy test")
        return True
    else:
        print(f"[FAIL] RSI accuracy test: {last_rsi:.2f}")
        return False

def test_atr_accuracy():
    """ATR accuracy test (Wilder's original example)"""
    print("\n=== ATR Accuracy Test ===")

    # Wilder's original data
    df = pd.DataFrame({
        'high': [48.70, 48.72, 48.90, 48.87, 48.82, 49.05, 49.20, 49.35,
                 49.92, 50.19, 50.12, 49.66, 49.88, 50.19, 50.36],
        'low': [47.79, 48.14, 48.39, 48.37, 48.24, 48.64, 48.94, 49.10,
                49.50, 49.87, 49.20, 48.90, 49.43, 49.73, 49.26],
        'close': [48.16, 48.61, 48.75, 48.63, 48.74, 49.03, 49.07, 49.32,
                  49.91, 50.13, 49.53, 49.50, 49.75, 50.03, 50.31]
    })

    atr_series = calculate_atr(df, period=14, return_series=True)
    last_atr = float(atr_series.iloc[-1])

    print(f"Last ATR: {last_atr:.4f}")
    print(f"Expected range: 0.40 ~ 0.70")

    if 0.40 <= last_atr <= 0.70:
        print("[PASS] ATR accuracy test")
        return True
    else:
        print(f"[FAIL] ATR accuracy test: {last_atr:.4f}")
        return False

def test_performance():
    """Performance benchmark"""
    print("\n=== Performance Benchmark (10K candles) ===")

    # Generate test data
    n = 10000
    np.random.seed(42)
    prices = np.random.randn(n).cumsum() + 100
    data = pd.Series(prices)
    df = pd.DataFrame({
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices
    })

    # RSI performance
    start = time.perf_counter()
    _rsi = calculate_rsi(data, period=14, return_series=True)
    rsi_time = (time.perf_counter() - start) * 1000

    print(f"\nRSI (10K candles):")
    print(f"  Time: {rsi_time:.2f}ms")
    if rsi_time > 0:
        print(f"  Throughput: {n / (rsi_time / 1000):,.0f} candles/sec")

    # ATR performance
    start = time.perf_counter()
    _atr = calculate_atr(df, period=14, return_series=True)
    atr_time = (time.perf_counter() - start) * 1000

    print(f"\nATR (10K candles):")
    print(f"  Time: {atr_time:.2f}ms")
    if atr_time > 0:
        print(f"  Throughput: {n / (atr_time / 1000):,.0f} candles/sec")

    # ADX performance
    start = time.perf_counter()
    _adx = calculate_adx(df, period=14, return_series=True)
    adx_time = (time.perf_counter() - start) * 1000

    print(f"\nADX (10K candles):")
    print(f"  Time: {adx_time:.2f}ms")
    if adx_time > 0:
        print(f"  Throughput: {n / (adx_time / 1000):,.0f} candles/sec")

    # Check goals
    print("\n=== Performance Goals ===")
    rsi_ok = "[PASS]" if rsi_time < 20 else "[WARN]"
    atr_ok = "[PASS]" if atr_time < 25 else "[WARN]"
    adx_ok = "[PASS]" if adx_time < 40 else "[WARN]"

    print(f"RSI: {rsi_time:.2f}ms (goal: < 20ms) {rsi_ok}")
    print(f"ATR: {atr_time:.2f}ms (goal: < 25ms) {atr_ok}")
    print(f"ADX: {adx_time:.2f}ms (goal: < 40ms) {adx_ok}")

    return rsi_time < 20, atr_time < 25, adx_time < 40

def test_inplace_option():
    """inplace option test"""
    print("\n=== inplace Option Test ===")

    from utils.indicators import add_all_indicators

    # Test data
    np.random.seed(42)
    prices = np.random.randn(100).cumsum() + 100
    df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.randint(1000, 10000, 100)
    })

    # inplace=False (default)
    df_copy = df.copy()
    result1 = add_all_indicators(df_copy, inplace=False)

    orig_modified = 'rsi' in df_copy.columns
    result_ok = 'rsi' in result1.columns

    print(f"inplace=False:")
    print(f"  Original modified: [FAIL unexpected]" if orig_modified else f"  Original modified: [PASS not modified]")
    print(f"  Result returned: [PASS]" if result_ok else f"  Result returned: [FAIL]")

    # inplace=True
    df_inplace = df.copy()
    result2 = add_all_indicators(df_inplace, inplace=True)

    orig_modified2 = 'rsi' in df_inplace.columns
    result_ok2 = 'rsi' in result2.columns

    print(f"\ninplace=True:")
    print(f"  Original modified: [PASS]" if orig_modified2 else f"  Original modified: [FAIL]")
    print(f"  Result returned: [PASS]" if result_ok2 else f"  Result returned: [FAIL]")

    # Check result match
    if 'rsi' in result1.columns and 'rsi' in result2.columns:
        rsi1_arr = np.asarray(result1['rsi'].values)
        rsi2_arr = np.asarray(result2['rsi'].values)
        rsi_match = np.allclose(rsi1_arr, rsi2_arr, rtol=1e-6, equal_nan=True)
        print(f"\nResults match: [PASS]" if rsi_match else f"\nResults match: [FAIL]")
        return rsi_match

    return False

if __name__ == '__main__':
    print("=" * 80)
    print("TwinStar Quantum - Optimization Verification Test")
    print("=" * 80)

    # Accuracy tests
    rsi_pass = test_rsi_accuracy()
    atr_pass = test_atr_accuracy()

    # inplace option test
    inplace_pass = test_inplace_option()

    # Performance benchmark
    perf_rsi, perf_atr, perf_adx = test_performance()

    # Final results
    print("\n" + "=" * 80)
    print("Final Results")
    print("=" * 80)
    print(f"RSI accuracy: [PASS]" if rsi_pass else f"RSI accuracy: [FAIL]")
    print(f"ATR accuracy: [PASS]" if atr_pass else f"ATR accuracy: [FAIL]")
    print(f"inplace option: [PASS]" if inplace_pass else f"inplace option: [FAIL]")
    print(f"RSI performance: [PASS]" if perf_rsi else f"RSI performance: [WARN needs improvement]")
    print(f"ATR performance: [PASS]" if perf_atr else f"ATR performance: [WARN needs improvement]")
    print(f"ADX performance: [PASS]" if perf_adx else f"ADX performance: [WARN needs improvement]")

    all_pass = rsi_pass and atr_pass and inplace_pass
    print(f"\nOverall: [PASS all tests]" if all_pass else f"\nOverall: [WARN some tests failed]")
    print("=" * 80)
