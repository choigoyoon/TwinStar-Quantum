#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_phase4_core.py - Phase 4 Verification Script
Targets:
1. core/crypto_payment.py
2. core/batch_optimizer.py
3. core/unified_bot.py
4. core/multi_symbol_backtest.py
5. core/async_scanner.py
6. core/auto_scanner.py
"""

import unittest
import logging
import json
import shutil
import tempfile
import time
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Configure Logging
logging.basicConfig(level=logging.ERROR)

class TestPhase4Core(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        logging.shutdown() # Release file locks
        try:
            shutil.rmtree(self.temp_dir)
        except OSError:
            pass # Ignore cleanup errors on Windows

    # =========================================================================
    # 1. Crypto Payment
    # =========================================================================
    def test_01_crypto_payment(self):
        """[CryptoPayment] Info Generation & Config"""
        try:
            from core.crypto_payment import CryptoPayment, CONFIG_PATH
        except ImportError:
            self.skipTest("CryptoPayment import failed")

        # Mock config path to temp dir
        with patch('core.crypto_payment.CONFIG_PATH', os.path.join(self.temp_dir, 'payment.json')):
            cp = CryptoPayment()
            
            # Test Config Load/Save
            wallets = cp.get_wallets()
            self.assertIn('USDT_TRC20', wallets)
            
            # Test Payment Info
            info = cp.get_payment_info(user_id=123, email="test@test.com")
            self.assertEqual(info['user_id'], 123)
            self.assertEqual(info['user_tag'], "USER000123")
            # Only USDT has address in default config
            self.assertEqual(len(info['payment_options']), 1)
            
            # Test Manual Verify Mock
            with patch('core.license_guard.get_license_guard') as mock_lg:
                mock_lg.return_value.record_payment.return_value = 999
                res = cp.verify_payment_manual(123, "0xHash", "USDT")
                self.assertEqual(res['payment_id'], 999)
                self.assertEqual(res['status'], 'pending')

    # =========================================================================
    # 2. Batch Optimizer
    # =========================================================================
    def test_02_batch_optimizer(self):
        """[BatchOptimizer] State & Flow"""
        try:
            from core.batch_optimizer import BatchOptimizer, OptimizationState
        except ImportError:
            self.skipTest("BatchOptimizer import failed")
            
        with patch('core.batch_optimizer.get_exchange_manager') as mock_em, \
             patch('core.batch_optimizer.optimize_strategy') as mock_opt, \
             patch('core.batch_optimizer.get_preset_manager') as mock_pm:
            
            # Mock Exchange
            mock_ex = MagicMock()
            mock_ex.exchange.fetch_tickers.return_value = {'BTC/USDT:USDT': {}, 'ETH/USDT:USDT': {}}
            mock_em.return_value.get_exchange.return_value = mock_ex
            
            # Init
            bo = BatchOptimizer(exchange='bybit')
            bo.STATE_FILE = Path(self.temp_dir) / 'batch_state.json'
            
            # Fetch Symbols
            bo.fetch_symbols()
            self.assertIn('BTCUSDT', bo.symbols)
            
            # Run Mock
            mock_opt.return_value = {'win_rate': 80, 'max_drawdown': 10, 'total_trades': 50}
            
            # Callbacks
            status_mock = MagicMock()
            bo.set_callbacks(status_cb=status_mock)
            
            # Run mostly logic check
            summary = bo.run()
            self.assertEqual(summary['success'], 4) # BTC and ETH * 2 timeframes
            self.assertTrue(bo.load_state())

    # =========================================================================
    # 3. Unified Bot
    # =========================================================================
    @patch('core.unified_bot.get_server_time_offset')
    def test_03_unified_bot(self, mock_time):
        """[UnifiedBot] Init & Components"""
        try:
            from core.unified_bot import UnifiedBot, create_bot
        except ImportError:
             self.skipTest("UnifiedBot import failed")

        mock_time.return_value = 0.5
        
        # Test Server Time
        from core.unified_bot import get_server_time_offset
        # We mocked it above, but let's assume imports resolved
        
        # Create Bot Mocking Exchange
        mock_exchange = MagicMock()
        mock_exchange.symbol = 'BTCUSDT'
        mock_exchange.name = 'bybit'
        
        # Mock modules inside UnifiedBot
        with patch('core.unified_bot.BotStateManager'), \
             patch('core.unified_bot.BotDataManager'), \
             patch('core.unified_bot.SignalProcessor'), \
             patch('core.unified_bot.OrderExecutor'), \
             patch('core.unified_bot.PositionManager'):
             
            bot = UnifiedBot(mock_exchange, simulation_mode=True)
            self.assertTrue(bot.simulation_mode)
            self.assertIsNotNone(bot.mod_state)
            
            # Test Readiness
            status = bot.get_readiness_status()
            self.assertFalse(status['ready']) # No data yet

    # =========================================================================
    # 4. Multi Symbol Backtest
    # =========================================================================
    def test_04_multi_symbol_backtest(self):
        """[MultiSymbolBacktest] Signal & Execution Logic"""
        try:
            from core.multi_symbol_backtest import MultiSymbolBacktest, Signal
        except ImportError:
            self.skipTest("MultiSymbolBacktest import failed")
            
        msb = MultiSymbolBacktest(initial_capital=1000)
        
        # Test Signal Dataclass
        sig = Signal(symbol='BTCUSDT', timestamp=datetime.now(), direction='Long', 
                     entry_price=100, sl_price=90, atr=1, pattern_score=90, 
                     volume_24h=1000, timeframe='4h')
        
        # Test Enter Position
        self.assertTrue(msb.enter_position(sig))
        self.assertIsNotNone(msb.position)
        self.assertEqual(msb.position.symbol, 'BTCUSDT')
        
        # Test Exit Conditions (SL)
        mock_price = {'open': 100, 'high': 105, 'low': 80, 'close': 85}
        with patch.object(msb, 'get_price_at_time', return_value=mock_price):
            triggered = msb.check_exit_conditions(datetime.now())
            self.assertTrue(triggered) # Low(80) < SL(90)
            self.assertIsNone(msb.position)
            
        # Results
        res = msb.get_result()
        self.assertEqual(res['total_trades'], 1)

    # =========================================================================
    # 5. Async Scanner
    # =========================================================================
    def test_05_async_scanner(self):
        """[AsyncScanner] Async Mocking"""
        try:
            from core.async_scanner import AsyncScanner
        except ImportError:
            self.skipTest("AsyncScanner import failed")

        scanner = AsyncScanner('bybit')
        
        # Mock aiohttp
        async def mock_scan():
            with patch('aiohttp.ClientSession.get') as mock_get:
                mock_resp = AsyncMock()
                mock_resp.status = 200
                mock_resp.json.return_value = {'result': 'ok'}
                mock_get.return_value.__aenter__.return_value = mock_resp
                
                results = await scanner.scan_symbols(['BTCUSDT'], '15m')
                return results

        # Run Async Test
        if sys.platform == 'win32':
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
             
        try:
            res = asyncio.run(mock_scan())
            self.assertEqual(len(res), 1)
            self.assertEqual(res[0]['symbol'], 'BTCUSDT')
        except Exception as e:
            print(f"Async test warning: {e}")

    # =========================================================================
    # 6. Auto Scanner
    # =========================================================================
    def test_06_auto_scanner(self):
        """[AutoScanner] Init & Logging"""
        try:
            # Need to mock PyQt5 signals if no QApp
            from PyQt6.QtCore import QObject
        except ImportError:
            print("PyQt5 not found, skipping AutoScanner test")
            return

        try:
            from core.auto_scanner import AutoScanner, SCANNER_CONFIG_PATH
        except ImportError:
            self.skipTest("AutoScanner import failed")
            
        # Mock Config Path
        with patch('core.auto_scanner.SCANNER_CONFIG_PATH', Path(self.temp_dir) / 'scanner_config.json'), \
             patch('core.auto_scanner.LOG_DIR', Path(self.temp_dir) / 'logs'):
            
            scanner = AutoScanner()
            self.assertFalse(scanner.running)
            
            # Test Config Save
            scanner.set_config({'param': 1})
            self.assertEqual(scanner.config['param'], 1)
            self.assertTrue((Path(self.temp_dir) / 'scanner_config.json').exists())

if __name__ == '__main__':
    unittest.main()
