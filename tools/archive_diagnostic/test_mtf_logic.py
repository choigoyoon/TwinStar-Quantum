
import pandas as pd
import numpy as np
import os
import sys

# Ensure core can be imported
sys.path.append(os.getcwd())

from core.strategy_core import AlphaX7Core
from core.multi_symbol_backtest import MultiSymbolBacktest
from utils.data_utils import resample_data
from indicator_generator import IndicatorGenerator

def run_variant(name, entry_price_mode, locked_mtf):
    msb = MultiSymbolBacktest(exchange='bybit')
    df_15m_raw = msb.load_candle_data('BTCUSDT', '15m')
    if df_15m_raw is None: return None

    df_pattern = resample_data(df_15m_raw, '1h', add_indicators=True)
    df_entry = IndicatorGenerator.add_all_indicators(df_15m_raw.copy())
    
    # Dec 22 JSON Parameters (The "High Win Rate" params)
    params = {
        'atr_mult': 1.1,
        'trail_start_r': 1.0,
        'trail_dist_r': 0.15,
        'pattern_tolerance': 0.05,
        'entry_validity_hours': 12.0,
        'filter_tf': '4h',
        'slippage': 0.0
    }
    
    core = AlphaX7Core(use_mtf=True)
    
    # Monkey patch the logic inside run_backtest for the test
    # We will temporarily modify the core attributes or use a custom method
    
    import types
    
    def custom_run(self, df_entry, df_pattern, df_filter=None, **kwargs):
        # We'll just use the logic from the file but with variants
        # Since we can't easily patch the loop without rewriting, we'll use the variants I've identified
        return self._run_backtest_internal_variant(df_entry, df_pattern, entry_price_mode, locked_mtf, **kwargs)

    # Note: _run_backtest_internal_variant is a helper we'd need to define or just hardcode the logic here
    # For speed, I'll just write a standalone simplified evaluator for this 4-way comparison
    
    # ... Simplified evaluation logic ...
    # Instead of monkeypatching, let's just use the current strategy_core.py as the "Honest" base
    # and I'll modify it manually between runs. 

if __name__ == "__main__":
    # Variant 1: Current (Honest)
    # Variant 2: Honest Entry + Late MTF (shift(1) removed)
    # Variant 3: Fake Entry + Locked MTF
    # Variant 4: Fake Entry + Late MTF (The 84% way)
    print("Please run this test manually by swapping code in strategy_core.py")
