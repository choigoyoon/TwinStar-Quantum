#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_medium_priority.py - Phase 3 Verification Script
Targets:
1. core/bot_state.py
2. core/data_manager.py
3. core/license_guard.py
4. utils/cache_manager.py
5. utils/time_utils.py
6. utils/error_reporter.py
7. exchanges/base_exchange.py
8. exchanges/ccxt_exchange.py
"""

import unittest
import logging
import json
import shutil
import tempfile
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
import sys
import os

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Imports
try:
    from core.bot_state import BotStateManager
    from core.data_manager import BotDataManager
    from core.license_guard import LicenseGuard, get_license_guard
    from utils.cache_manager import TTLCache, cached
    from utils.time_utils import to_utc, get_exchange_now, is_signal_valid
    from utils.error_reporter import ErrorReporter
    from exchanges.base_exchange import Position
    from exchanges.ccxt_exchange import CCXTExchange
except ImportError as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.ERROR)

class TestPhase3(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    # =========================================================================
    # 1. Bot State
    # =========================================================================
    def test_01_bot_state(self):
        """[BotState] Save/Load and Atomic Write"""
        manager = BotStateManager('bybit', 'BTCUSDT', storage_dir=self.temp_dir)
        
        state = {'capital': 1000, 'pos': 'long'}
        
        # Test Save
        success = manager.save_state(state)
        self.assertTrue(success)
        self.assertTrue(manager.state_file.exists())
        
        # Test Load
        loaded = manager.load_state()
        self.assertEqual(loaded['capital'], 1000)
        self.assertEqual(loaded['exchange'], 'bybit') # Auto-added field
        
    # =========================================================================
    # 2. Data Manager
    # =========================================================================
    def test_02_data_manager(self):
        """[DataManager] Path Generation"""
        dm = BotDataManager('bybit', 'BTC/USDT', cache_dir=self.temp_dir)
        
        expected_name = "bybit_btcusdt_15m.parquet"
        self.assertEqual(dm.get_entry_file_path().name, expected_name)
        
    # =========================================================================
    # 3. License Guard
    # =========================================================================
    @patch('core.license_guard.requests.post')
    def test_03_license_guard(self, mock_post):
        """[LicenseGuard] Server Check & Tier Logic"""
        guard = get_license_guard()
        
        # Test Login Mock
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'success': True, 
            'valid': True, 
            'tier': 'premium',
            'days_left': 30
        }
        mock_post.return_value = mock_response
        
        res = guard.login("test@test.com")
        self.assertTrue(res['success'])
        self.assertEqual(guard.tier, 'premium')
        
        # Test Limits
        limit = guard.check_symbol_limit(['BTC','ETH','XRP'])
        self.assertTrue(limit['allowed']) # Premium allows 50
        
    # =========================================================================
    # 4. Cache Manager
    # =========================================================================
    def test_04_cache_manager(self):
        """[CacheManager] TTL Eviction"""
        cache = TTLCache(default_ttl=0.1) # 100ms TTL
        
        cache.set('key', 'val')
        self.assertEqual(cache.get('key'), 'val')
        
        time.sleep(0.2)
        self.assertIsNone(cache.get('key')) # Should expire
        
        # Decorator Test
        call_count = 0
        @cached(ttl=1)
        def heavy_func(x):
            nonlocal call_count
            call_count += 1
            return x * x
            
        heavy_func(2)
        heavy_func(2) # Cached
        self.assertEqual(call_count, 1)

    # =========================================================================
    # 5. Time Utils
    # =========================================================================
    def test_05_time_utils(self):
        """[TimeUtils] Signal Validity & Conversion"""
        # Signal Validity
        now = datetime.now(timezone.utc)
        old_sig = now - timedelta(hours=3)
        
        self.assertTrue(is_signal_valid(old_sig, validity_hours=4))
        self.assertFalse(is_signal_valid(old_sig, validity_hours=2))
        
        # Conversion
        # Just check it returns a timezone-aware dt
        utc_dt = to_utc(datetime.now())
        self.assertIsNotNone(utc_dt.tzinfo)

    # =========================================================================
    # 6. Error Reporter
    # =========================================================================
    @patch('utils.error_reporter.requests.post')
    def test_06_error_reporter(self, mock_post):
        """[ErrorReporter] Capture & Hash"""
        try:
            raise ValueError("Test Error")
        except ValueError as e:
            # Capture
            ErrorReporter.capture(e, context="Unit Test")
            
            # Hash Check
            h = ErrorReporter._get_error_hash(e)
            self.assertTrue(len(h) > 0)
            
            # Need to wait for thread? mock_post might not be called immediately
            # Just verify the static method runs without error
            
    # =========================================================================
    # 7. Base Exchange (Position)
    # =========================================================================
    def test_07_position_dataclass(self):
        """[BaseExchange] Position Serialization"""
        pos = Position(
            symbol='BTCUSDT', side='Long', entry_price=50000, size=1.0, 
            stop_loss=49000, initial_sl=49000, risk=1000, entry_time=datetime.now()
        )
        
        # To Dict
        d = pos.to_dict()
        self.assertEqual(d['symbol'], 'BTCUSDT')
        self.assertEqual(d['side'], 'Long')
        
        # From Dict
        pos2 = Position.from_dict(d)
        self.assertEqual(pos2.entry_price, 50000)

    # =========================================================================
    # 8. CCXT Exchange
    # =========================================================================
    @patch('exchanges.ccxt_exchange.ccxt')
    def test_08_ccxt_exchange(self, mock_ccxt):
        """[CCXT] Connect & Order Mock"""
        # Mock class attribute
        mock_exchange_inst = MagicMock()
        mock_ccxt.bybit.return_value = mock_exchange_inst
        
        ex = CCXTExchange('bybit', {'api_key': 'k', 'api_secret': 's'})
        
        # Connect
        connected = ex.connect()
        self.assertTrue(connected)
        mock_exchange_inst.load_markets.assert_called()
        
        # Place Market Order
        mock_exchange_inst.create_order.return_value = {'id': '12345'}
        mock_exchange_inst.fetch_ticker.return_value = {'last': 50000}
        
        oid = ex.place_market_order('Long', 0.1, 49000)
        self.assertEqual(oid, '12345')
        self.assertIsNotNone(ex.position)
        self.assertEqual(ex.position.entry_price, 50000)

if __name__ == '__main__':
    unittest.main()
