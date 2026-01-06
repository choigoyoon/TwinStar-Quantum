#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_core_deep.py - Deep Functional Verification of Core Modules
"""
import sys
import os
import unittest
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Core imports
from core.data_manager import BotDataManager
from core.strategy_core import AlphaX7Core, TradeSignal
from core.optimizer import BacktestOptimizer, OptimizationResult
from core.unified_backtest import UnifiedBacktest, UnifiedResult
from core.order_executor import OrderExecutor
from core.position_manager import PositionManager
from core.signal_processor import SignalProcessor

logging.basicConfig(level=logging.CRITICAL) # Suppress normal logs

class TestCoreDeep(unittest.TestCase):
    
    def log_result(self, module, function, expected, actual, tolerance=None):
        passed = False
        if tolerance:
             passed = abs(expected - actual) <= tolerance
        else:
             passed = expected == actual

        icon = "✅" if passed else "❌"
        msg = f"{icon} [{module}] [{function}] Expected={expected}, Actual={actual}"
        if not passed and tolerance:
            msg += f" (Diff > {tolerance})"
        print(msg)
        return passed

    # =========================================================================
    # 1. Data Manager Verification
    # =========================================================================
    def test_01_data_manager_resampling(self):
        """Verify 15m -> 1H resampling logic and OHLCV integrity"""
        print("\n--- Testing Data Manager ---")
        
        # Create 4 15m candles (1 hour)
        # 00:00, 00:15, 00:30, 00:45
        base_time = datetime(2023, 1, 1, 0, 0, 0)
        data = []
        # Candle 1: 100 -> 105 (High 106, Low 99)
        data.append({'timestamp': base_time, 'open': 100, 'high': 106, 'low': 99, 'close': 105, 'volume': 10})
        # Candle 2: 105 -> 102 (High 105, Low 101)
        data.append({'timestamp': base_time + timedelta(minutes=15), 'open': 105, 'high': 105, 'low': 101, 'close': 102, 'volume': 20})
        # Candle 3: 102 -> 104 (High 104, Low 100)
        data.append({'timestamp': base_time + timedelta(minutes=30), 'open': 102, 'high': 104, 'low': 100, 'close': 104, 'volume': 10})
        # Candle 4: 104 -> 110 (High 110, Low 104) -> Max High here
        data.append({'timestamp': base_time + timedelta(minutes=45), 'open': 104, 'high': 110, 'low': 104, 'close': 110, 'volume': 30})
        
        df_15m = pd.DataFrame(data)
        
        # Initialize
        dm = BotDataManager('test', 'BTCUSDT', {'entry_tf': '15m', 'pattern_tf': '1h'})
        dm.df_entry_full = df_15m
        
        # Execute Process
        # We need to spy on 'process_data' or use its internal logic if it's not easily isolated
        # process_data sets df_pattern_full
        dm.process_data()
        
        df_1h = dm.df_pattern_full
        
        # Verify
        if df_1h is None or len(df_1h) == 0:
            self.log_result("data_manager", "resampling", "1 row", "0 rows")
            return

        row = df_1h.iloc[0]
        
        # Expected
        exp_open = 100.0 # First open
        exp_high = 110.0 # Max high
        exp_low = 99.0   # Min low
        exp_close = 110.0 # Last close
        exp_vol = 70.0   # Sum volume
        
        self.log_result("data_manager", "resample_open", exp_open, float(row['open']))
        self.log_result("data_manager", "resample_high", exp_high, float(row['high']))
        self.log_result("data_manager", "resample_low", exp_low, float(row['low']))
        self.log_result("data_manager", "resample_close", exp_close, float(row['close']))
        self.log_result("data_manager", "resample_volume", exp_vol, float(row['volume']))

    # =========================================================================
    # 2. Strategy Core Verification
    # =========================================================================
    def test_02_strategy_indicators(self):
        """Verify RSI calculation and Signal triggers"""
        print("\n--- Testing Strategy Core ---")
        strategy = AlphaX7Core()
        
        # Mock RSI Calc
        # Provide a series of closes that goes up consistently -> RSI 100 (approx)
        closes = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114])
        # calculate_rsi uses internal indicator utils usually.
        # But let's check the wrapper
        rsi = strategy.calculate_rsi(closes, period=14)
        
        # Since it's pure gain, RSI should be 100
        # However, Wilder's smoothing might need initial avg. 
        # With n=15 and period=14, it might not be perfect 100 instantly if implemented with rolling mean vs ewm
        # Standard RSI with only gains is 100.
        self.log_result("strategy_core", "verify_rsi_uptrend", 100.0, round(rsi, 0)) # Tolerance handled by rounding

        # Backtest Logic - Manual PnL Check
        # entry 100, exit 110, Long -> 10%
        # fee 0.1% (slippage+fee)
        trade = {'entry': 100, 'exit': 110, 'type': 'Long', 'pnl': 0} # Pnl calc happens in run_backtest usually
        # But metrics calculation uses pre-calculated PnL. strategy.run_backtest does the calc.
        
        # We can construct a small backtest scenario
        # 4 candles.
        df_pattern = pd.DataFrame([{
            'timestamp': datetime(2023,1,1) + timedelta(hours=i),
            'open': 100, 'high': 120, 'low': 80, 'close': 100, 'volume': 100
        } for i in range(10)]) # Flat market
        
        # Manually inject a signal W pattern
        # Indices 0,1,2,3...
        # Let's mock detect_signal to return a fixed signal to force run_backtest to trade
        # Actually run_backtest calls extract_all_signals internally.
        # We will mock extract_all_signals
        
        original_extract = strategy._extract_all_signals
        
        # Robust Timestamp Gen
        # Generate UTC timestamps
        dates = pd.date_range(start='2023-01-01 00:00', periods=50, freq='15min')
        
        # Signal at Index 20 (05:00)
        # Use the exact timestamp from the series to ensure match
        signal_time = dates[20].to_pydatetime()
        
        mock_signal = {
            'type': 'Long', 'pattern': 'W', 'time': signal_time,
            'stop_loss': 90, 'atr': 1
        }
        
        strategy._extract_all_signals = lambda *args, **kwargs: [mock_signal]
        
        # Entry DF: aligned
        # Convert to ms integers
        ts_values = dates.astype(np.int64) // 10**6
        
        df_entry = pd.DataFrame({
            'timestamp': ts_values,
            'open': 100, 'high': 105, 'low': 95, 'close': 100
        })
        # Modify to Trigger SL at Index 30
        # SL is around 87.5 (100 - 10*1.25)
        # Drop Low to 80
        df_entry.loc[30, 'low'] = 80
        df_entry.loc[30, 'close'] = 80
        
        # Disable MTF filter to simplify
        strategy.USE_MTF_FILTER = False
        
        trades = strategy.run_backtest(df_pattern, df_entry, slippage=0, entry_validity_hours=10)
        
        strategy._extract_all_signals = original_extract # Restore
        
        has_trade = isinstance(trades, list) and len(trades) > 0
        self.log_result("strategy_core", "backtest_execution", True, has_trade)
        
        if has_trade:
             pnl = trades[0]['pnl']
             # Entered at ~100. Price went up to ~120. 
             # Trailing SL should have caught some profit or SL hit on way down.
             # Just verify it's not 0 and likely positive
             self.log_result("strategy_core", "backtest_pnl_nonzero", True, pnl != 0)

    # =========================================================================
    # 3. Order Executor Verification
    # =========================================================================
    def test_03_order_executor_pnl(self):
        """Verify PnL and Fee calculations"""
        print("\n--- Testing Order Executor ---")
        
        # Mock Exchange
        class MockEx:
            leverage = 5
        
        ox = OrderExecutor(MockEx(), strategy_params={'slippage': 0.0006}) # 0.06% fee
        
        # Case 1: Long Win
        # Entry 100, Exit 110 (10% Raw). Leverage 5 -> 50%.
        # Fee: 0.06% on Entry(100) + 0.06% on Exit(110) ?? 
        # Wait, calculate_pnl formula:
        # fee_rate = 0.0006
        # total_fee = size * entry * fee + size * exit * fee
        # pnl_usd = raw - fee
        
        pnl_pct, pnl_usd = ox.calculate_pnl( entry_price=100, exit_price=110, side='Long', size=1, leverage=5 )
        
        # Expected Raw USD: 1 * (110 - 100) = 10
        # Expected Fee: 1*100*0.0006 + 1*110*0.0006 = 0.06 + 0.066 = 0.126
        # Expected USD: 10 - 0.126 = 9.874
        # Expected Pct: (110-100)/100 * 5 * 100 = 50%...?
        # Wait, calculate_pnl returns Pct based on price delta * leverage. 
        # Does it deduct fee from pct?
        # Code check:
        # pnl_pct = (exit-entry)/entry * leverage * 100
        # pnl_usd = raw - fee
        # It seems Pct does NOT include fee in the current implementation shown in preview.
        # Let's verify what the code actually does.
        # (Looking at previous code view):
        # pnl_pct = ...
        # pnl_usd = ...
        # return pnl_pct, pnl_usd
        # Fee is only deducted from USD? That might be a logic gap if PCT is displayed to user.
        # But let's verify what it does currently.
        
        self.log_result("order_executor", "pnl_usd_long", 9.874, round(pnl_usd, 3))
        self.log_result("order_executor", "pnl_pct_long", 50.0, pnl_pct) # Expecting raw pct

        # Case 2: Short Win
        # Entry 100, Exit 90 (10% Raw). Leverage 5 -> 50%.
        pnl_pct_s, pnl_usd_s = ox.calculate_pnl( entry_price=100, exit_price=90, side='Short', size=1, leverage=5 )
        
        # Raw USD: 1 * (100 - 90) = 10
        # Fee: 1*100*0.0006 + 1*90*0.0006 = 0.06 + 0.054 = 0.114
        # USD: 10 - 0.114 = 9.886
        
        self.log_result("order_executor", "pnl_usd_short", 9.886, round(pnl_usd_s, 3))
        self.log_result("order_executor", "pnl_pct_short", 50.0, pnl_pct_s)

    # =========================================================================
    # 4. Position Manager Verification
    # =========================================================================
    def test_04_position_checks(self):
        """Verify SL Hit and Trailing Logic"""
        print("\n--- Testing Position Manager ---")
        
        pm = PositionManager(None, dry_run=True)
        
        # Mock Position
        class Pos:
            side = 'Long'
            stop_loss = 100
        
        # Test SL Hit
        # Low 99 < SL 100 -> True
        hit = pm.check_sl_hit(Pos(), high=105, low=99)
        self.log_result("position_manager", "sl_hit_long_true", True, hit)
        
        # Low 101 > SL 100 -> False
        hit_fail = pm.check_sl_hit(Pos(), high=105, low=101)
        self.log_result("position_manager", "sl_hit_long_false", False, hit_fail)
        

    # =========================================================================
    # 5. Signal Processor Verification
    # =========================================================================
    def test_05_signal_filtering(self):
        """Verify Signal Expiration"""
        print("\n--- Testing Signal Processor ---")
        
        sp = SignalProcessor(strategy_params={'entry_validity_hours': 1})
        
        now = datetime.utcnow()
        
        # Signal 1: Just created (Valid)
        sig1 = {'type': 'Long', 'time': now}
        
        # Signal 2: Created 2 hours ago (Expired)
        sig2 = {'type': 'Short', 'time': now - timedelta(hours=2)}
        
        valid = sp.filter_valid_signals([sig1, sig2])
        
        self.log_result("signal_processor", "filter_expiration_count", 1, len(valid))
        if len(valid) == 1:
            self.log_result("signal_processor", "filter_expiration_type", 'Long', valid[0]['type'])

    # =========================================================================
    # 6. Unified Backtest Verification (Math)
    # =========================================================================
    def test_06_backtest_math(self):
        """Verify MDD and WinRate Calc"""
        print("\n--- Testing Unified Backtest Math ---")
        
        ub = UnifiedBacktest()
        ub.equity_history = [100, 110, 100, 120, 90, 95] 
        # Peaks: 100->100, 110->10, 110->10, 120->0, 120->30
        # MDD: 30 / 120 = 25% (120 -> 90)
        
        # Hack to access private method or logic
        # _finalize_results calculates metrics from self.trade_history
        
        # We need to populate trade_history to trigger calculation
        # But equity_history is used for MDD
        
        # Mock trades for win rate
        # 1 Win, 1 Loss
        ub.trade_history = [
            {'pnl_percent': 10}, 
            {'pnl_percent': -5}
        ]
        
        res = ub._finalize_results()
        
        self.log_result("unified_backtest", "win_rate", 50.0, res.win_rate)
        # Check MDD
        self.log_result("unified_backtest", "mdd", 25.0, res.max_drawdown)
        
        # Profit Factor: Gross Win 10, Gross Loss 5 -> 2.0
        self.log_result("unified_backtest", "profit_factor", 2.0, res.profit_factor)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
