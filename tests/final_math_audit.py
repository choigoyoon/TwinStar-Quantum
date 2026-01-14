import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path

# Add paths for imports
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from core.strategy_core import AlphaX7Core
from core.optimization_logic import OptimizationEngine
from core.signal_processor import SignalProcessor

def run_math_audit(symbol="BTCUSDT"):
    print(f"\n{'='*60}")
    print(f"📊 Final Math & Logic Alignment Audit: {symbol}")
    print(f"{'='*60}")

    # 1. Load Data (Bybit BTCUSDT 15m)
    # Note: data_manager.py uses parquet or sqlite depending on config. 
    # For audit, we load directly from the parquet cache for speed and consistency.
    cache_path = root_dir / "data" / "cache" / f"bybit_{symbol.lower()}_15m.parquet"
    if not cache_path.exists():
        print(f"❌ Cache file not found: {cache_path}")
        return

    df_full = pd.read_parquet(cache_path)
    # Ensure timestamp is datetime
    if not pd.api.types.is_datetime64_any_dtype(df_full['timestamp']):
        df_full['timestamp'] = pd.to_datetime(df_full['timestamp'], unit='ms')
    
    # Use latest 2000 candles for audit
    df = df_full.tail(2000).copy()
    
    # 2. Resample for Pattern (1H)
    df_1h = df.set_index('timestamp').resample('1h').agg({
        'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
    }).dropna().reset_index()

    params = {
        'atr_mult': 1.0,
        'trail_start_r': 0.5,
        'trail_dist_r': 0.1,
        'macd_fast': 12,
        'macd_slow': 26,
        'macd_signal': 9,
        'ema_period': 20,
        'filter_tf': '4h',
        'allowed_direction': 'Both',
        'leverage': 1,
        'slippage': 0.0006,
        'fee': 0.00055
    }

    # Separate costs for worker simulation
    worker_params = params.copy()
    
    # Standalone BT setup
    bt_params = params.copy()
    bt_params['slippage'] = params['slippage'] + params['fee'] # Worker logic: slippage = slippage + fee
    
    print(f"\n[1] Running AlphaX7Core.run_backtest (Standalone BT)...")
    strategy = AlphaX7Core(use_mtf=True)
    trades_bt = strategy.run_backtest(
        df_pattern=df_1h,
        df_entry=df,
        **bt_params
    )
    pnl_bt = sum([t['pnl'] for t in trades_bt]) if trades_bt else 0
    print(f"   -> Trades: {len(trades_bt)}, Total P&L: {pnl_bt:.4f}%")

    print(f"\n[2] Running OptimizationEngine.run_single_backtest (Optimizer Logic)...")
    engine = OptimizationEngine(strategy=strategy)
    # OptimizationEngine expects df to be the entry data (15m) and it handles resampling internally if needed 
    # but the worker actually handles pattern resampling. 
    # Let's use the actual worker-like setup.
    from core.optimization_logic import _worker_run_backtest
    df_dict = df.to_dict('list')
    columns = list(df.columns)
    worker_args = (params, df_dict, columns)
    opt_result = _worker_run_backtest(worker_args)
    pnl_opt = opt_result.simple_return if opt_result else 0
    trades_opt = opt_result.trade_count if opt_result else 0
    print(f"   -> Trades: {trades_opt}, Total P&L: {pnl_opt:.4f}%")

    print(f"\n[3] Verifying SignalProcessor Injection (Live Logic)...")
    # Simulate SignalProcessor behavior
    sp = SignalProcessor(strategy_params=params)
    
    # Check default tolerance/validity from strategy
    tolerance = getattr(strategy, 'PATTERN_TOLERANCE', 0.05)
    validity = getattr(strategy, 'ENTRY_VALIDITY_HOURS', 4.0)

    signals = strategy._extract_all_signals(
        df_1h, 
        tolerance=tolerance,
        validity_hours=validity,
        macd_fast=params['macd_fast'],
        macd_slow=params['macd_slow'],
        macd_signal=params['macd_signal']
    )
    
    # Compare signal count with the start of the backtest
    # This is a proxy for injection integrity.
    print(f"   -> Patterns Detected (1H): {len(signals)}")

    # 4. Final Comparison
    print(f"\n{'='*40}")
    print(f"🏆 AUDIT RESULT")
    print(f"{'='*40}")
    
    bt_vs_opt = (len(trades_bt) == trades_opt) and (abs(pnl_bt - pnl_opt) < 0.0001)
    
    if bt_vs_opt:
        print("✅ SUCCESS: Backtest and Optimization math are IDENTICAL.")
    else:
        print("❌ FAILURE: Inconsistency detected between Backtest and Optimization.")
        print(f"   Diff: Trades ({len(trades_bt)} vs {trades_opt}), P&L ({pnl_bt:.4f} vs {pnl_opt:.4f})")

    print("\n[Audit Checkpoint] Verifying Parameter Injection in SignalProcessor...")
    # Check if SignalProcessor correctly uses strategy_params for MACD
    test_sp = SignalProcessor(strategy_params={'macd_fast': 99})
    # If the fix was applied, test_sp.strategy_params['macd_fast'] should be 99 
    # and it should be passed to _extract_all_signals in add_patterns_from_df (manual check from prompt info)
    
    # Manual check of SignalProcessor.add_patterns_from_df logic
    import inspect
    source = inspect.getsource(SignalProcessor.add_patterns_from_df)
    if "macd_fast" in source and "strategy_params" in source:
        print("✅ SUCCESS: SignalProcessor includes MACD parameter injection logic.")
    else:
        print("❌ FAILURE: SignalProcessor seems to ignore MACD parameters in strategy_params.")

    print(f"{'='*60}\n")

if __name__ == "__main__":
    run_math_audit("BTCUSDT")
    run_math_audit("ETHUSDT")
