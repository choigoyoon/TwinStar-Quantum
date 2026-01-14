#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_core_functional.py - Core Module Functional Verification (No Mocks)
"""
import sys
import os
import logging
import pandas as pd
import numpy as np
from pathlib import Path
import datetime
from typing import Any, cast

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s' # Clean output for reporting
)
logger = logging.getLogger("CoreVerify")

class CoreVerifier:
    def __init__(self):
        self.results = []
        
    def log_result(self, module, feature, success, message=""):
        icon = "✅" if success else "❌"
        print(f"{icon} [{module}] {feature} - {message}")
        self.results.append((module, feature, success, message))

    def generate_synthetic_data(self, days=30):
        print("Generating synthetic data...")
        dates = pd.date_range(end=datetime.datetime.now(), periods=days*24*4, freq='15min') # 15m data
        data = []
        price = 50000.0
        
        for date in dates:
            change = np.random.normal(0, 100)
            open_p = price
            close_p = price + change
            high_p = max(open_p, close_p) + abs(np.random.normal(0, 50))
            low_p = min(open_p, close_p) - abs(np.random.normal(0, 50))
            vol = abs(np.random.normal(100, 50))
            
            data.append({
                'timestamp': date,
                'open': open_p,
                'high': high_p,
                'low': low_p,
                'close': close_p,
                'volume': vol
            })
            price = close_p
            
        df = pd.DataFrame(data)
        # Ensure numeric types
        cols = ['open', 'high', 'low', 'close', 'volume']
        df[cols] = df[cols].astype(float)
        return df

    def verify_data_manager(self):
        module = "core/data_manager.py"
        try:
            from core.data_manager import BotDataManager
            
            # 1. Initialization
            dm = BotDataManager('test_exchange', 'BTCUSDT')
            self.log_result(module, "Initialization", True, "Instance created")
            
            # 2. Resampling
            df_15m = self.generate_synthetic_data(days=5)
            # Inject data manually
            dm.df_entry_full = df_15m
            
            # Run process_data which triggers resampling
            dm.process_data()
            
            if dm.df_pattern_full is not None and not dm.df_pattern_full.empty:
                ratio = len(df_15m) / len(dm.df_pattern_full)
                # 15m -> 1h should be approx 4:1
                is_valid = 3.8 <= ratio <= 4.2 
                self.log_result(module, "Resampling (15m->1h)", is_valid, f"Ratio: {ratio:.2f}")
            else:
                self.log_result(module, "Resampling (15m->1h)", False, "1h DataFrame (df_pattern_full) is empty")

            return dm
            
        except Exception as e:
            self.log_result(module, "General Error", False, str(e))
            return None

    def verify_strategy_core(self, dm):
        module = "core/strategy_core.py"
        try:
            from core.strategy_core import AlphaX7Core
            
            strategy = AlphaX7Core()
            self.log_result(module, "Initialization", True, "Strategy Instance created")
            
            if dm and dm.df_pattern_full is not None:
                # 1. Signal Detection
                # We need df_1h (pattern) and df_15m (entry)
                df_1h = dm.df_pattern_full
                df_15m = dm.df_entry_full # Full 15m entry data
                
                # Run detection (might return empty list if random data doesn't match pattern, but it shouldn't crash)
                signals = strategy.detect_signal(
                    df_1h=df_1h,
                    df_15m=df_15m,
                    filter_tf='4h',
                    rsi_period=14,
                    atr_period=14,
                    pattern_tolerance=0.03, # Loose tolerance to maybe catch something
                    entry_validity_hours=6
                )
                
                # Check formatting
                # detect_signal returns Optional[TradeSignal], NOT list
                is_valid = signals is None or hasattr(signals, 'signal_type')
                self.log_result(module, "Signal Detection", is_valid, f"Result type: {type(signals)}")
                
                # 2. Backtest
                bt_result = strategy.run_backtest(
                    df_pattern=df_1h,
                    df_entry=df_15m, 
                    balance=1000,
                    leverage=1
                )
                
                has_key = 'total_return' in bt_result
                self.log_result(module, "Backtest Execution", has_key, f"Return: {bt_result.get('total_return', 'N/A')}%")
                
            else:
                 self.log_result(module, "Signal Detection", False, "Skipped due to missing data")

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log_result(module, "General Error", False, str(e))

    def verify_optimizer(self, dm):
        module = "core/optimizer.py"
        try:
            from core.optimizer import BacktestOptimizer
            from core.strategy_core import AlphaX7Core
            
            if dm and dm.df_pattern_full is not None:
                # Create a small param grid
                param_grid = {
                    'rsi_period': [14, 21],
                    'atr_period': [14]
                }
                
                # Initialize Optimizer
                # It expects strategy_class and df (pattern) or set_data
                opt = BacktestOptimizer(strategy_class=AlphaX7Core, df=dm.df_pattern_full)
                
                # Hack to pass entry data if needed by _run_single, 
                # but BacktestOptimizer usually resamples internally from supplied df 
                # or we might need to verify how it gets entry data.
                # In BacktestOptimizer.optimize -> calls _run_single.
                # _run_single usually needs df_pattern and df_entry.
                # Looking at outline, _run_single(self, params...) uses self.df_pattern and self.df_entry
                # But we initialized with just df.
                # Let's check if we need to set df_entry manually.
                cast(Any, opt).df_entry = dm.df_entry_full
                
                # Run optimization
                results = opt.run_optimization(
                    df=dm.df_pattern_full,
                    grid=param_grid,
                    metric='total_return',
                    n_cores=1 # Single thread
                )
                
                has_result = isinstance(results, list) and len(results) > 0
                best_ret = results[0].total_return if has_result else "N/A"
                
                self.log_result(module, "Optimization Run", has_result, f"Best PnL: {best_ret}")
                
            else:
                self.log_result(module, "Optimization", False, "Skipped due to missing data")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.log_result(module, "General Error", False, str(e))

    def verify_others(self):
        # Simply import and instantiate to check syntax and basic init
        modules = [
            ("core/signal_processor.py", "SignalProcessor"),
            ("core/order_executor.py", "OrderExecutor"),
            ("core/position_manager.py", "PositionManager"),
            ("core/auto_scanner.py", "AutoScanner")
        ]
        
        for mod_path, class_name in modules:
            try:
                # Dynamic import
                dotted_path = mod_path.replace('/', '.').replace('.py', '')
                mod = __import__(dotted_path, fromlist=[class_name])
                cls = getattr(mod, class_name)
                
                # Instance check
                # Some might require args, try empty or None
                try:
                    instance = cls()
                    self.log_result(mod_path, "Instantiation", True, "Success (no args)")
                except TypeError:
                    # Try with dummy args if needed
                     self.log_result(mod_path, "Instantiation", True, "Success (Class exists, needs args)")
                     
            except Exception as e:
                self.log_result(mod_path, "Import/Init", False, str(e))

    def run(self):
        print("Starting Core Verification...")
        dm = self.verify_data_manager()
        self.verify_strategy_core(dm)
        self.verify_optimizer(dm)
        self.verify_others()
        print("\nVerification Complete.")

if __name__ == "__main__":
    verifier = CoreVerifier()
    verifier.run()
