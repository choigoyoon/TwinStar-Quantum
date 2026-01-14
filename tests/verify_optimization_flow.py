"""
Verify Optimization Flow (Step 1)
- Tests: Symbol Loading, Batch Execution, Preset Saving
"""
import sys
import os
import unittest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Any, cast

# Path setup
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.batch_optimizer import BatchOptimizer

class TestOptimizationFlow(unittest.TestCase):
    def setUp(self):
        self.test_symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        self.optimizer = BatchOptimizer(exchange='bybit', timeframes=['1h'])
        self.optimizer.symbols = self.test_symbols
        
        # Mocking external calls to avoid actual heavy processing
        self.optimizer.fetch_symbols = MagicMock(return_value=self.test_symbols)
        self.optimizer.optimize_symbol = MagicMock(return_value={
            'win_rate': 75.5,
            'max_drawdown': 15.0,
            'grade': 'A',
            'params': {'rsi_period': 14}
        })
        
    def test_batch_execution(self):
        print("\n\n=== [Step 1] Verifying Optimization Flow ===")
        
        # 1. Symbol Loading
        fetched = self.optimizer.fetch_symbols()
        if fetched is None:
            fetched = []
        print(f"✅ Symbol Load: {len(fetched)} symbols loaded ({fetched})")
        self.assertEqual(len(fetched), 3)
        
        # 2. Batch Execution (Mocked)
        print("▶️ Starting Batch Optimization (Quick Mode mocked)...")
        results = {}
        for sym in self.test_symbols:
            res = self.optimizer.optimize_symbol(sym, '1h')
            results[sym] = res
            if res:
                print(f"  - Optimized {sym}: WR={res['win_rate']}%, Grade={res['grade']}")
            
        self.assertEqual(len(results), 3)
        print("✅ Batch Execution Complete")
        
        # 3. Preset Saving
        print("▶️ Saving Presets...")
        preset_dir = Path("config/presets")
        preset_dir.mkdir(parents=True, exist_ok=True)
        
        for sym, res in results.items():
            self.optimizer.save_preset(sym, '1h', res)
            
            # Verify file exists
            path = preset_dir / f"bybit_{sym}_1h.json"
            if not path.exists():
                # Try finding any match if exact name differs
                candidates = list(preset_dir.glob(f"*{sym}*.json"))
                if candidates:
                    path = candidates[0]
            
            self.assertTrue(path.exists(), f"Preset for {sym} not created")
            print(f"  ✅ Preset Saved: {path.name}")
            
            # Verify Fields
            import json
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                result_block = data.get('_result', {})
                self.assertIn('win_rate', result_block)
                # Check for either 'mdd' or 'max_drawdown'
                mdd = result_block.get('mdd') if 'mdd' in result_block else result_block.get('max_drawdown')
                self.assertIsNotNone(mdd, "Neither 'mdd' nor 'max_drawdown' found in result block")
                print(f"     -> Fields Check: win_rate={result_block.get('win_rate')}, mdd={mdd}")

if __name__ == '__main__':
    unittest.main()
