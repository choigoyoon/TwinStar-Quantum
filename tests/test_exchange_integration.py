#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_exchange_integration.py - Exchange Adapter Integration Verification
"""
import unittest
import logging
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys
import os
import pandas as pd
from datetime import datetime

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from exchanges.binance_exchange import BinanceExchange
from exchanges.base_exchange import Position

# --- Mock Responses for Binance API ---
MOCK_ACCOUNT = {
    'totalWalletBalance': '10000.00',
    'positions': [
        {'symbol': 'BTCUSDT', 'positionAmt': '0.1', 'entryPrice': '50000', 'unRealizedProfit': '50', 'leverage': '10'}
    ]
}

MOCK_KLINES = [
    [
        1672531200000, # Open time
        "16500.00",    # Open
        "16550.00",    # High
        "16480.00",    # Low
        "16520.00",    # Close
        "150.00",      # Volume
        1672534799999, # Close time
        "2400000.00",  # Quote asset volume
        100,           # Number of trades
        "50.00",       # Taker buy base asset volume
        "800000.00",   # Taker buy quote asset volume
        "0"            # Ignore
    ] for _ in range(100)
]

MOCK_ORDER_RESP = {
    'orderId': 123456789,
    'symbol': 'BTCUSDT',
    'status': 'NEW',
    'clientOrderId': 'testOrder',
    'price': '0',
    'avgPrice': '0',
    'origQty': '0.1',
    'executedQty': '0',
    'cumQuote': '0',
    'timeInForce': 'GTC',
    'type': 'MARKET',
    'reduceOnly': False,
    'closePosition': False,
    'side': 'BUY',
    'positionSide': 'BOTH',
    'stopPrice': '0',
    'workingType': 'CONTRACT_PRICE',
    'priceProtect': False,
    'origType': 'MARKET',
    'time': 1672531200000,
    'updateTime': 1672531200000
}

MOCK_TICKER = {'symbol': 'BTCUSDT', 'price': '50000.00'}

MOCK_EXCHANGE_INFO = {
    'symbols': [
        {'symbol': 'BTCUSDT', 'status': 'TRADING', 'baseAsset': 'BTC', 'quoteAsset': 'USDT'},
        {'symbol': 'ETHUSDT', 'status': 'TRADING', 'baseAsset': 'ETH', 'quoteAsset': 'USDT'}
    ]
}

class TestExchangeIntegration(unittest.TestCase):
    
    def setUp(self):
        # Configure logging to show verify steps
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        self.config = {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'symbol': 'BTCUSDT',
            'testnet': True
        }
    
    @patch('exchanges.binance_exchange.Client')
    @patch('exchanges.binance_exchange.get_secure_storage')
    def test_full_integration(self, mock_storage, mock_client_cls):
        print("\n=== Exchange Integration Test (Binance) ===")
        
        # Setup Mock Client Instance
        client = MagicMock()
        mock_client_cls.return_value = client
        
        # Setup Storage values
        storage_instance = MagicMock()
        storage_instance.get_exchange_keys.return_value = {'api_key': 'k', 'api_secret': 's'}
        mock_storage.return_value = storage_instance
        
        # Apply Mocks to Client Methods
        client.futures_account.return_value = MOCK_ACCOUNT
        client.futures_klines.return_value = MOCK_KLINES
        client.futures_symbol_ticker.return_value = MOCK_TICKER
        client.futures_create_order.return_value = MOCK_ORDER_RESP
        client.futures_change_leverage.return_value = {'symbol': 'BTCUSDT', 'leverage': 10}
        client.futures_exchange_info.return_value = MOCK_EXCHANGE_INFO
        client.futures_position_information.return_value = MOCK_ACCOUNT['positions']
        client.get_server_time.return_value = {'serverTime': 1672531200000}
        
        # Instantiate Adapter
        exchange = BinanceExchange(self.config)
        
        # ============================================
        # 1. Connection / Auth
        # ============================================
        print("[1/7] Connection/Auth...")
        connected = exchange.connect()
        self.assertTrue(connected)
        self.assertTrue(exchange.authenticated)
        print(f"✅ Connected. Balance: {exchange.get_balance()} USDT")
        
        # ============================================
        # 2. Data Fetching
        # ============================================
        print("[2/7] Data Fetching...")
        
        df = exchange.get_klines('15m', limit=100)
        self.assertIsNotNone(df)
        if df is not None:
            self.assertEqual(len(df), 100)
            self.assertIn('close', df.columns)
            print(f"✅ OHLCV Fetched: {len(df)} candles")
        
        # Ticker
        price = exchange.get_current_price()
        self.assertEqual(price, 50000.0)
        print(f"✅ Current Price: {price}")
        
        # ============================================
        # 3. Account Info
        # ============================================
        print("[3/7] Account Info...")
        
        balance = exchange.get_balance()
        self.assertEqual(balance, 10000.00)
        
        # Implementation specific: get_positions might differ in base
        if hasattr(exchange, 'get_positions'):
            positions = exchange.get_positions()
            if positions: # Check for None or empty
                self.assertEqual(len(positions), 1)
                print(f"✅ Positions Fetched: {len(positions)}")
            
        print("✅ Account Info Verified")
        
        # ============================================
        # 4. Order Management
        # ============================================
        print("[4/7] Order Management...")
        
        # Create Order
        print("  -> Placing Market Long...")
        order_id = exchange.place_market_order(side='Long', size=0.1, stop_loss=49000)
        self.assertTrue(order_id)
        # Verify calls
        # 1. Main Order
        # 2. SL Order
        self.assertEqual(client.futures_create_order.call_count, 2)
        print(f"✅ Order Placed. ID: {order_id}")
        
        # ============================================
        # 5. Leverage
        # ============================================
        print("[5/7] Leverage/Margin...")
        success = exchange.set_leverage(10)
        self.assertTrue(success)
        client.futures_change_leverage.assert_called_with(symbol='BTCUSDT', leverage=10)
        print("✅ Leverage Set to 10x")
        
        # ============================================
        # 6. WebSocket (Mocked)
        # ============================================
        print("[6/7] WebSocket...")
        # Since start_websocket imports locally from exchanges.ws_handler
        with patch('exchanges.ws_handler.WebSocketHandler') as mock_ws_cls:
            mock_ws = MagicMock()
            mock_ws_cls.return_value = mock_ws
            
            # Since we can't easily await in sync test without asyncio loop, 
            # we check if class handles it logically.
            with patch('asyncio.create_task'):
                # start_websocket is async, so we just call it (it returns coroutine)
                # But wait, it's defined as 'async def'. Calling it returns a coroutine.
                # It won't execute body unless awaited.
                # We need to wrap it or use async test runner.
                # However, for simple verification, we can just check if it IS async.
                
                # To execute it:
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(exchange.start_websocket(on_price_update=lambda x: None))
                
                mock_ws_cls.assert_called()
                print("✅ WebSocket Handler Initialized")
        
        # ============================================
        # 7. Error Handling
        # ============================================
        print("[7/7] Error Handling...")
        
        # Simulate API Error
        client.futures_create_order.side_effect = Exception("API Error")
        res = exchange.place_market_order('Short', 0.1, 51000)
        self.assertFalse(res)
        print("✅ API Error Handled Gracefully")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
