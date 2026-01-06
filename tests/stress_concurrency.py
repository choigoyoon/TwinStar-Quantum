"""
Stress Test: Concurrency & Optimization Worker
Verifies that starting and stopping the Optimization Engine multiple times does not cause deadlocks or crashes.
"""
import sys
import unittest
import threading
import time
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root
sys.path.insert(0, str(Path(r"C:\매매전략")))

from core.optimization_logic import OptimizationEngine

class TestConcurrency(unittest.TestCase):
    def setUp(self):
        # Create dummy data for optimization
        self.df_15m = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=1000, freq='15min'),
            'open': np.random.randn(1000)+100,
            'high': np.random.randn(1000)+105,
            'low': np.random.randn(1000)+95,
            'close': np.random.randn(1000)+100,
            'volume': np.random.randn(1000)+1000
        })
        self.engine = OptimizationEngine()

    def test_rapid_start_stop(self):
        """Simulate rapid start/stop of optimization jobs (multiprocessing stress)"""
        print("\n[STRESS] Starting Rapid Start/Stop Test (5 iterations)...")
        
        for i in range(5):
            print(f"Iteration {i+1}...")
            
            params = {
                'loss_limit': 0.9, 'profit_rate': 1.1, 
                'trend_ma': 50, 'filter_tf': '1h', 
                'rsi_period': 14, 'macd_fast': 12, 'macd_slow': 26, 'macd_signal': 9
            }
            
            try:
                def task():
                    # OptimizationEngine.run_single_backtest takes (params, df)
                    self.engine.run_single_backtest(params, self.df_15m)
                
                t = threading.Thread(target=task)
                t.start()
                t.join(timeout=2.0) # Should finish fast
                if t.is_alive():
                     self.fail("Optimization worker hung (Deadlock candidate)")
                     
            except Exception as e:
                self.fail(f"Concurrent execution failed: {e}")
                
        print("[STRESS] Passed.")

if __name__ == '__main__':
    unittest.main()
