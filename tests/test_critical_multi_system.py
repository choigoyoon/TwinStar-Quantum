#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_critical_multi_system.py - Verification for Critical Modules (Part B)
Target: MultiCoinSniper, MultiTrader
"""
import unittest
import logging
import threading
import time
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path
import sys
import os

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from core.multi_sniper import MultiCoinSniper
from core.multi_trader import MultiTrader

logging.basicConfig(level=logging.INFO)

class TestCriticalMultiSystem(unittest.TestCase):
    
    def setUp(self):
        self.mock_license = MagicMock()
        self.mock_license.get_current_tier.return_value = 'PREMIUM'
        
        self.mock_exchange_client = MagicMock()
        
    # =========================================================================
    # 1. MultiCoinSniper Tests
    # =========================================================================
    def test_01_sniper_init(self):
        """[MultiSniper] Initialize loads top coins"""
        sniper = MultiCoinSniper(
            self.mock_license, self.mock_exchange_client, total_seed=1000
        )
        
        # Mock _get_top_by_volume instead of requests
        with patch.object(sniper, '_get_top_by_volume', return_value=['BTCUSDT', 'ETHUSDT']), \
             patch.object(sniper, '_fetch_latest_data', return_value=True), \
             patch.object(sniper, '_load_params', return_value={}), \
             patch.object(sniper, '_quick_backtest', return_value=85.0):
            
            sniper.initialize(exchange='bybit')
                
            # Check coins loaded
            self.assertIn('BTCUSDT', sniper.coins)
            self.assertIn('ETHUSDT', sniper.coins)
            # Check status
            self.assertEqual(sniper.coins['BTCUSDT'].backtest_winrate, 85.0)
            
        print("✅ [MultiSniper] Initialization verified")

    def test_02_sniper_entry(self):
        """[MultiSniper] Candle close triggers entry"""
        sniper = MultiCoinSniper(
            self.mock_license, self.mock_exchange_client, total_seed=1000
        )
        
        # Setup Coin State
        from core.multi_sniper import CoinState, CoinStatus
        sniper.coins['BTCUSDT'] = CoinState(
            symbol='BTCUSDT', initial_seed=100, seed=100, params={'leverage': 3},
            status = CoinStatus.WATCH
        )
        
        # Mock _try_entry to verify call
        with patch.object(sniper, '_try_entry') as mock_entry, \
             patch.object(sniper, '_calc_readiness', return_value=95.0), \
             patch.object(sniper, '_save_candle_to_parquet'):
            
            # Simulate Candle Close (readiness 95 > 90 threshold)
            kline = {'symbol': 'BTCUSDT', 'close': 50000, 'confirm': True}
            
            # Call on_candle_close (Note signature: exchange, symbol, candle)
            sniper.on_candle_close(exchange='bybit', symbol='BTCUSDT', candle=kline)
            
            # Since readiness is mocked to 95, it should trigger entry
            # and update status to READY
            self.assertEqual(sniper.coins['BTCUSDT'].status, CoinStatus.READY)
            mock_entry.assert_called_with('bybit', 'BTCUSDT', kline)
            
        print("✅ [MultiSniper] Entry trigger logic verified")

    # =========================================================================
    # 2. MultiTrader Tests (Rotation)
    # =========================================================================
    def test_03_trader_rotation(self):
        """[MultiTrader] Subscription Rotation Logic"""
        trader = MultiTrader(
            self.mock_license, self.mock_exchange_client, total_seed=1000
        )
        trader.ws_slots = 2 # Limit slots to test rotation
        
        # Add 4 dummy coins
        from core.multi_trader import CoinState
        for sym in ['A', 'B', 'C', 'D']:
            trader.all_coins[sym] = CoinState(symbol=sym, base_symbol=sym, params={})
            
        # Round 0
        batch1 = trader.get_rotation_batch()
        self.assertEqual(len(batch1), 2)
        self.assertEqual(set(batch1), {'A', 'B'})
        
        # Round 1
        batch2 = trader.get_rotation_batch()
        self.assertEqual(len(batch2), 2)
        self.assertEqual(set(batch2), {'C', 'D'})
        
        # Round 2 (Wrap around)
        batch3 = trader.get_rotation_batch()
        self.assertEqual(len(batch3), 2)
        self.assertEqual(set(batch3), {'A', 'B'})
        
        print("✅ [MultiTrader] Rotation logic verified")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
