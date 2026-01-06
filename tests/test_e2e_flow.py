#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_e2e_flow.py - End-to-End Integration Test for Trading Pipeline
"""
import unittest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys
import os

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from core.strategy_core import AlphaX7Core
from core.optimization_logic import OptimizationEngine
from core.auto_scanner import AutoScanner

class TestE2EFlow(unittest.TestCase):
    def setUp(self):
        # Generate Synthetic Data (Uptrend/W-Pattern hybrid to trigger signals)
        self.df = self._generate_synthetic_data(1000)
        
    def _generate_synthetic_data(self, length):
        # Create timestamps
        dates = pd.date_range(end=pd.Timestamp.now(), periods=length, freq='15min')
        
        # Create Price Movement: Sine wave + Trend + Noise
        x = np.linspace(0, 20*np.pi, length)
        trend = np.linspace(10000, 11000, length)
        wave = 200 * np.sin(x)
        noise = np.random.normal(0, 10, length)
        
        # Base Close Price
        close = trend + wave + noise
        
        # OHLC generation
        df = pd.DataFrame(index=dates)
        df['close'] = close
        # Add some volatility for High/Low
        volatility = np.abs(np.random.normal(0, 20, length)) + 5
        df['open'] = close + np.random.normal(0, 10, length)
        df['high'] = df[['open', 'close']].max(axis=1) + volatility
        df['low'] = df[['open', 'close']].min(axis=1) - volatility
        df['volume'] = 1000 + np.abs(np.random.normal(0, 500, length))
        df['timestamp'] = df.index
        
        # Ensure numeric for calculations
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
            
        return df

    def test_full_pipeline(self):
        print("\n=== E2E Integration Test Pipeline ===")
        
        # =========================================================
        # [1/5] Data -> Strategy
        # =========================================================
        print("[1/5] Data -> Strategy Signal Check...")
        strategy = AlphaX7Core()
        
        # Run Backtest on synthetic data to check for signals
        # We need to ensure columns match what strategy expects
        # AlphaX7 core handles 'timestamp' or index.
        
        # Providing simple data. The synthetic data has wave patterns which might trigger W/M detection.
        # Even if 0 trades, we confirm the method executes without error.
        trades = strategy.run_backtest(self.df, self.df)
        
        self.assertIsInstance(trades, list)
        print(f"✅ Data processed. Strategy trace found {len(trades)} potential trades (Flow OK).")
        
        # =========================================================
        # [2/5] Strategy -> Optimization
        # =========================================================
        print("[2/5] Strategy -> Optimization Check...")
        engine = OptimizationEngine(strategy=strategy)
        
        # Small grid for speed verification
        grid = engine.generate_grid_from_options({
            'atr_mult': [1.0, 1.5, 2.0],
            'leverage': [1]
        })
        
        # Mock task callback
        mock_callback = MagicMock()
        
        # Run optimization
        results = engine.run_optimization(self.df, grid, max_workers=1, task_callback=mock_callback)
        
        self.assertTrue(len(results) > 0)
        
        # Select best
        best_results = engine.get_best_params(results, top_n=1)
        self.assertTrue(len(best_results) > 0)
        best_result = best_results[0]
        best_params = best_result.params
        
        print(f"✅ Optimization complete. Scanned {len(results)} combos. Best Params: {best_params.get('atr_mult')}")
        
        # =========================================================
        # [3/5] Optimization -> Backtest (Verification)
        # =========================================================
        print("[3/5] Optimization -> Backtest Check...")
        
        # Run backtest with optimized params
        verify_trades = strategy.run_backtest(self.df, self.df, **best_params)
        
        self.assertIsNotNone(verify_trades)
        # We assume optimization returned valid result that produces trades or at least metric calculation
        pnls = [t['pnl'] for t in verify_trades]
        total_pnl = sum(pnls) if pnls else 0
        
        print(f"✅ Backtest verified using optimized params. Trades: {len(verify_trades)}, PnL: {total_pnl:.2f}%")
        
        # =========================================================
        # [4/5] Backtest -> Scanner (Selection)
        # =========================================================
        print("[4/5] Backtest -> Scanner Selection Check...")
        
        # Simulate Scanner verifying symbols using PresetManager
        with patch('core.auto_scanner.get_preset_manager') as mock_pm_loader:
             # Mock PresetManager Instance
             mock_pm = MagicMock()
             # Simulate finding our 'Verified' preset
             mock_pm.list_presets.return_value = ['Bybit_BTCUSDT_optimized']
             # Simulate stats
             mock_pm.get_verification_status.return_value = {
                 'win_rate': 75.5, 
                 'profit_factor': 2.0,
                 'verified': True
             } 
             # Simulate loading params
             mock_pm.load_preset.return_value = {'params': best_params}
             
             mock_pm_loader.return_value = mock_pm
             
             scanner = AutoScanner()
             scanner.load_verified_symbols()
             
             self.assertEqual(len(scanner.verified_symbols), 1)
             target = scanner.verified_symbols[0]
             self.assertEqual(target['symbol'], 'BTCUSDT')
             self.assertEqual(target['params'], best_params)
             
             print(f"✅ Scanner loaded verified symbol: {target['symbol']} (MOCKED)")

        # =========================================================
        # [5/5] Scanner -> Execution (Dry Run)
        # =========================================================
        print("[5/5] Scanner -> Execution Check...")
        
        # Verify _execute_entry calls exchange calls correctly
        
        with patch('core.auto_scanner.get_exchange_manager') as mock_em_loader:
            mock_em = MagicMock()
            mock_exchange = MagicMock()
            
            # Setup Exchange Mock
            current_price = 50000.0
            mock_exchange.get_current_price.return_value = current_price
            mock_exchange.create_order.return_value = {'orderId': '12345', 'status': 'FILLED'}
            
            mock_em.get_exchange.return_value = mock_exchange
            mock_em_loader.return_value = mock_em
            
            # Setup Opportunity
            scanner.config = {'entry_amount': 100, 'leverage': 3, 'max_positions': 5}
            opp = {
                'symbol': 'BTCUSDT',
                'exchange': 'Bybit',
                'direction': 'Long',
                'params': best_params
            }
            
            # Trigger Execution
            scanner._execute_entry(opp)
            
            # Assertions
            mock_exchange.get_current_price.assert_called_with('BTCUSDT')
            mock_exchange.create_order.assert_called_once()
            
            # Verify Arguments
            call_args = mock_exchange.create_order.call_args[1]
            self.assertEqual(call_args['symbol'], 'BTCUSDT')
            self.assertEqual(call_args['type'], 'market')
            self.assertEqual(call_args['side'], 'buy')
            
            # Verify Quantity Calculation: (100 * 3) / 50000 = 0.006
            expected_size = (100 * 3) / 50000.0
            self.assertAlmostEqual(call_args['amount'], expected_size)
            
            # Verify Signal Emitted (Assuming we can't easily catch signal in unit test without qApp, 
            # but we trust create_order is the physical termination point)
            
            print("✅ Execution signal sent to Exchange successfully.")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
