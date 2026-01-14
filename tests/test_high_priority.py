#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_high_priority.py - Phase 2 Verification Script
Targets:
1. core/optimization_logic.py
2. utils/indicators.py
3. utils/preset_storage.py
4. exchanges/exchange_manager.py
5. exchanges/ws_handler.py
"""

import unittest
import logging
import json
import shutil
import tempfile
import asyncio
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
import sys
import os

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Imports (wrapped in try-except for safety, though they should exist)
try:
    from core.optimization_logic import calculate_grade, passes_filter, OptimizationResult
    from utils.indicators import calculate_rsi, calculate_atr, calculate_macd
    from utils.preset_storage import PresetStorage
    from exchanges.exchange_manager import ExchangeManager, get_exchange_manager
    from exchanges.ws_handler import WebSocketHandler
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.ERROR) # Clean output

class TestPhase2(unittest.TestCase):
    
    # =========================================================================
    # 1. Optimization Logic
    # =========================================================================
    def test_01_optimization_logic(self):
        """[Optimization] Check grading and filtering logic"""
        # Test Grading
        self.assertEqual(calculate_grade(85, 12, 3.0), "🏆S")
        self.assertEqual(calculate_grade(75, 17, 2.0), "🥇A")
        self.assertEqual(calculate_grade(60, 20, 1.0), "🥉C")
        
        # Test Filter
        # Result(params, win_rate, simple, compound, mdd, sharpe, trades, pf)
        res_pass = OptimizationResult({}, 75.0, 0, 0, 15.0, 0, 300, 2.0)
        self.assertTrue(passes_filter(res_pass))
        
        res_fail_wr = OptimizationResult({}, 60.0, 0, 0, 15.0, 0, 300, 2.0)
        self.assertFalse(passes_filter(res_fail_wr))
        
        res_fail_mdd = OptimizationResult({}, 75.0, 0, 0, 25.0, 0, 300, 2.0)
        self.assertFalse(passes_filter(res_fail_mdd))
        
        print("✅ [Optimization] Logic verified")

    # =========================================================================
    # 2. Indicators
    # =========================================================================
    def test_02_indicators(self):
        """[Indicators] Check RSI, ATR accuracy"""
        # Create Dummy Data (Uptrend)
        closes = np.array([10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25])
        
        # RSI (Period 14) -> Uptrend should be high (100 in simple avg gain/loss if no loss)
        rsi = calculate_rsi(closes, period=14)
        self.assertEqual(rsi, 100.0) # No losses, so RSI 100
        
        # ATR
        df = pd.DataFrame({
            'high':  [10, 11, 12, 13, 14, 15],
            'low':   [ 9, 10, 11, 12, 13, 14],
            'close': [10, 11, 12, 13, 14, 15]
        }) # TR always 1 (H-L=1, H-Cp=1, L-Cp=1)
        
        atr = calculate_atr(df, period=5)
        self.assertAlmostEqual(atr, 1.0)
        
        print("✅ [Indicators] Math verified")

    # =========================================================================
    # 3. Preset Storage
    # =========================================================================
    def test_03_preset_storage(self):
        """[Storage] Save and Load Presets"""
        # Use temp directory
        temp_dir = tempfile.mkdtemp()
        try:
            storage = PresetStorage(base_path=temp_dir)
            
            params = {'a': 1, 'b': 2}
            res = {'win_rate': 80}
            
            # Save
            success = storage.save_preset('BTCUSDT', '1h', params, res)
            self.assertTrue(success)
            
            # Load
            loaded = storage.load_preset('BTCUSDT', '1h')
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded['params']['a'], 1)
            
            # Index check
            self.assertIn('BTCUSDT_1h', storage.index['presets'])
            
        finally:
            shutil.rmtree(temp_dir)
            
        print("✅ [Storage] I/O verified")

    # =========================================================================
    # 4. Exchange Manager
    # =========================================================================
    def test_04_exchange_manager(self):
        """[ExchangeManager] Singleton and Key Management"""
        em = get_exchange_manager()
        # Reset for test
        em.configs = {}
        em.exchanges = {}
        
        # Mock Connect
        with patch.object(em, '_connect', return_value=(True, "")):
            # Set Key
            success, msg = em.set_api_key('bybit', 'key', 'secret')
            self.assertTrue(success)
            self.assertIn('bybit', em.configs)
            self.assertEqual(em.configs['bybit'].api_key, 'key')
            
        # Mock Get Balance
        with patch.object(em, 'get_exchange') as mock_get_ex:
            mock_ex_instance = MagicMock()
            mock_ex_instance.fetch_balance.return_value = {'USDT': {'free': 1000.0}}
            mock_get_ex.return_value = mock_ex_instance
            
            bal = em.get_balance('bybit', 'USDT')
            self.assertEqual(bal, 1000.0)
            
        print("✅ [ExchangeManager] Manager verified")

    # =========================================================================
    # 5. WS Handler
    # =========================================================================
    def test_05_ws_handler(self):
        """[WSHandler] Parsing Logic"""
        handler = WebSocketHandler('bybit', 'BTCUSDT')
        
        # Test Bybit Parsing
        mock_data = {
            "topic": "kline.15.BTCUSDT",
            "data": [{
                "start": 1600000000000,
                "open": "50000",
                "close": "51000",
                "confirm": True
            }]
        }
        
        # Mock callback
        mock_cb = MagicMock()
        handler.on_candle_close = mock_cb
        
        # Verify parsing (Async run)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(handler._parse_bybit(mock_data))
        loop.close()
        
        # Check call
        self.assertTrue(mock_cb.called)
        args = mock_cb.call_args[0][0]
        self.assertEqual(args['close'], 51000.0)
        self.assertTrue(args['confirm'])
        
        print("✅ [WSHandler] Parsing verified")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
