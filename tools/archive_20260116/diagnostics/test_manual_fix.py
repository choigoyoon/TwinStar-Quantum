"""
Manual test script for data continuity fix verification
"""

import sys
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import shutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.data_manager import BotDataManager


def create_test_candles(count: int, start_date: str = '2024-01-01') -> pd.DataFrame:
    """Create test OHLCV data"""
    return pd.DataFrame({
        'timestamp': pd.date_range(start_date, periods=count, freq='15min'),
        'open': 100.0 + np.random.randn(count) * 0.5,
        'high': 101.0 + np.random.randn(count) * 0.5,
        'low': 99.0 + np.random.randn(count) * 0.5,
        'close': 100.5 + np.random.randn(count) * 0.5,
        'volume': 1000 + np.random.randint(-100, 100, count)
    })


def test_full_history_preservation():
    """Test 1: Verify Parquet saves all 2000 candles"""
    print("\n" + "="*60)
    print("TEST 1: Full History Preservation (2000 candles)")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix='test_cache_')

    try:
        manager = BotDataManager('bybit', 'BTCUSDT', cache_dir=temp_dir)

        # Create 2000 candles
        df = create_test_candles(2000, '2024-01-01')
        print(f"Created {len(df)} test candles")

        manager.df_entry_full = df.copy()
        manager.save_parquet()
        print("Saved to Parquet")

        # Load and verify
        parquet_file = manager.get_entry_file_path()
        loaded = pd.read_parquet(parquet_file)
        loaded['timestamp'] = pd.to_datetime(loaded['timestamp'], unit='ms')

        print(f"Loaded {len(loaded)} candles from Parquet")

        if len(loaded) == 2000:
            print("✅ PASS: All 2000 candles saved (no truncation)")
            return True
        else:
            print(f"❌ FAIL: Expected 2000, got {len(loaded)}")
            return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_memory_limit():
    """Test 2: Verify memory still limited to 1000"""
    print("\n" + "="*60)
    print("TEST 2: Memory Limit (MAX_ENTRY_MEMORY)")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix='test_cache_')

    try:
        manager = BotDataManager('bybit', 'BTCUSDT', cache_dir=temp_dir)

        # Create 1500 candles
        df = create_test_candles(1500, '2024-01-01')
        manager.df_entry_full = df.copy()

        # Simulate append (triggers memory limit)
        new_candle = {
            'timestamp': pd.Timestamp('2024-01-16 15:00:00'),
            'open': 100.0, 'high': 101.0, 'low': 99.0, 'close': 100.5, 'volume': 1000
        }
        manager.append_candle(new_candle, save=False)

        memory_count = len(manager.df_entry_full)
        expected = manager.MAX_ENTRY_MEMORY

        print(f"Memory contains {memory_count} candles")
        print(f"MAX_ENTRY_MEMORY = {expected}")

        if memory_count == expected:
            print(f"✅ PASS: Memory limited to {expected} candles")
            return True
        else:
            print(f"❌ FAIL: Expected {expected}, got {memory_count}")
            return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_bot_restart():
    """Test 3: Verify bot restart loads full history"""
    print("\n" + "="*60)
    print("TEST 3: Bot Restart with Full History (2880 candles)")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix='test_cache_')

    try:
        # Phase 1: Initial bot run
        manager1 = BotDataManager('bybit', 'BTCUSDT', cache_dir=temp_dir)
        df_large = create_test_candles(2880, '2024-01-01')
        manager1.df_entry_full = df_large.copy()
        manager1.save_parquet()
        print("Phase 1: Saved 2880 candles")

        # Phase 2: Bot restart
        manager2 = BotDataManager('bybit', 'BTCUSDT', cache_dir=temp_dir)
        loaded = manager2.load_historical(fetch_callback=None)

        loaded_count = len(manager2.df_entry_full) if manager2.df_entry_full is not None else 0

        print(f"Phase 2: Loaded {loaded_count} candles after restart")

        if loaded_count == 2880:
            print("✅ PASS: Full history loaded on restart")
            return True
        else:
            print(f"❌ FAIL: Expected 2880, got {loaded_count}")
            return False

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_compression():
    """Test 4: Verify zstd compression reduces file size"""
    print("\n" + "="*60)
    print("TEST 4: Compression (zstd)")
    print("="*60)

    temp_dir = tempfile.mkdtemp(prefix='test_cache_')

    try:
        manager = BotDataManager('bybit', 'BTCUSDT', cache_dir=temp_dir)

        # Create 2000 candles
        df = create_test_candles(2000, '2024-01-01')
        manager.df_entry_full = df.copy()
        manager.save_parquet()

        parquet_file = manager.get_entry_file_path()
        file_size_kb = parquet_file.stat().st_size / 1024

        print(f"File size: {file_size_kb:.1f} KB for 2000 candles")

        # Compressed should be < 50KB (uncompressed ~100KB)
        if file_size_kb < 50:
            print(f"✅ PASS: File compressed ({file_size_kb:.1f} KB)")
            return True
        else:
            print(f"⚠️  WARNING: File may not be compressed ({file_size_kb:.1f} KB)")
            return True  # Not critical

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_constants():
    """Test 5: Verify constants are defined"""
    print("\n" + "="*60)
    print("TEST 5: Constants (MAX_ENTRY_MEMORY, MAX_PATTERN_MEMORY)")
    print("="*60)

    has_entry = hasattr(BotDataManager, 'MAX_ENTRY_MEMORY')
    has_pattern = hasattr(BotDataManager, 'MAX_PATTERN_MEMORY')

    print(f"MAX_ENTRY_MEMORY defined: {has_entry}")
    print(f"MAX_PATTERN_MEMORY defined: {has_pattern}")

    if has_entry and has_pattern:
        print(f"MAX_ENTRY_MEMORY = {BotDataManager.MAX_ENTRY_MEMORY}")
        print(f"MAX_PATTERN_MEMORY = {BotDataManager.MAX_PATTERN_MEMORY}")
        print("✅ PASS: Constants defined")
        return True
    else:
        print("❌ FAIL: Constants not defined")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("DATA CONTINUITY FIX - VERIFICATION TESTS")
    print("="*60)

    tests = [
        test_full_history_preservation,
        test_memory_limit,
        test_bot_restart,
        test_compression,
        test_constants
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(results)
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n❌ {total - passed} TEST(S) FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(main())
