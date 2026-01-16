"""
Quick unit test to validate parallel worker fix
"""
import sys
from pathlib import Path
import pandas as pd

# Add project root
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.analyze_indicator_sensitivity import _run_single_backtest
from core.data_manager import BotDataManager
from utils.data_utils import resample_data

print("=" * 60)
print("Parallel Worker Function Unit Test")
print("=" * 60)

# Load real data
print("\n1. Loading data...")
manager = BotDataManager('bybit', 'BTCUSDT')
manager.load_historical()
df_15m = manager.df_entry_full
if df_15m is None or df_15m.empty:
    print("❌ Failed to load data")
    sys.exit(1)
df_1h = resample_data(df_15m, '1h')

print(f"   ✅ Loaded {len(df_15m)} 15m candles")
print(f"   ✅ Resampled to {len(df_1h)} 1h candles")

# Base parameters
base_params = {
    'rsi_period': 14,
    'rsi_overbought': 70,
    'rsi_oversold': 30,
    'atr_mult': 2.0,
    'tp_multiplier': 1.5,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'adx_period': 14,
    'adx_threshold': 25
}

# Test with single parameter value
print("\n2. Running parallel worker function...")
args = (14, df_1h, df_15m, base_params, 'rsi_period')

try:
    result = _run_single_backtest(args)

    print("\n3. Results:")
    print(f"   Success: {result['success']}")
    print(f"   Param Value: {result['param_value']}")
    print(f"   Win Rate: {result['win_rate']*100:.2f}%")
    print(f"   Total Return: {result['total_return']:.2f}%")
    print(f"   MDD: {result['mdd']:.2f}%")
    print(f"   Sharpe Ratio: {result['sharpe']:.2f}")
    print(f"   Trades: {result['trades']}")
    print(f"   Profit Factor: {result['profit_factor']:.2f}")

    # Validation checks
    print("\n4. Validation:")
    errors = []

    if not result['success']:
        errors.append(f"   ❌ Backtest failed: {result.get('error', 'Unknown error')}")
    else:
        print(f"   ✅ Backtest successful")

    if result['win_rate'] == 0 and result['total_return'] == 0:
        errors.append(f"   ⚠️  Warning: All metrics are zero (may indicate no trades)")
    else:
        print(f"   ✅ Metrics have non-zero values")

    if 'error' not in result:
        print(f"   ✅ No errors in result")

    if errors:
        print("\nErrors found:")
        for error in errors:
            print(error)
    else:
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)

except Exception as e:
    print(f"\n❌ TEST FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
