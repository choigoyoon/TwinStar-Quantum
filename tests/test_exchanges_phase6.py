import unittest
import sys
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

from exchanges.base_exchange import BaseExchange
from exchanges.binance_exchange import BinanceExchange
from exchanges.okx_exchange import OKXExchange
from exchanges.bitget_exchange import BitgetExchange
from exchanges.bingx_exchange import BingXExchange
from exchanges.upbit_exchange import UpbitExchange
from exchanges.bithumb_exchange import BithumbExchange

class TestPhase6Exchanges(unittest.TestCase):
    
    def setUp(self):
        self.config = {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'symbol': 'BTC/USDT',
            'testnet': True
        }
    
    def test_01_binance(self):
        """[Binance] Init & Methods"""
        with patch('exchanges.binance_exchange.Client') as MockClient, \
             patch('exchanges.binance_exchange.get_secure_storage'):
            
            # Setup Mock
            client = MockClient.return_value
            client.futures_account.return_value = {'totalWalletBalance': 1000}
            client.futures_get_position_mode.return_value = {'dualSidePosition': False}
            
            # Init
            ex = BinanceExchange(self.config)
            self.assertIsInstance(ex, BaseExchange)
            self.assertTrue(ex.connect())
            
            # Balance
            client.futures_account_balance.return_value = [{'asset': 'USDT', 'balance': '1000', 'withdrawAvailable': '1000'}]
            self.assertEqual(ex.get_balance(), 1000)
            
            # Price
            client.futures_symbol_ticker.return_value = {'price': '50000'}
            self.assertEqual(ex.get_current_price(), 50000)
            
            # Order
            client.futures_create_order.return_value = {'orderId': '12345'}
            self.assertTrue(ex.place_market_order('Long', 0.01, 49000))
            
            # Leverage
            ex.set_leverage(10)
            client.futures_change_leverage.assert_called()

    def test_02_okx(self):
        """[OKX] Init & Methods"""
        with patch('exchanges.okx_exchange.ccxt') as mock_ccxt:
            ex_mock = MagicMock()
            mock_ccxt.okx.return_value = ex_mock
            
            ex = OKXExchange(self.config)
            self.assertTrue(ex.connect())
            
            # Balance
            ex_mock.fetch_balance.return_value = {'USDT': {'free': 2000}}
            self.assertEqual(ex.get_balance(), 2000)
            
            # Price
            ex_mock.fetch_ticker.return_value = {'last': 60000}
            self.assertEqual(ex.get_current_price(), 60000)
            
            # Order
            ex_mock.create_order.return_value = {'id': 'okx_123'}
            self.assertEqual(ex.place_market_order('Long', 0.01, 59000), 'okx_123')
            
            # Leverage
            ex.set_leverage(5)
            ex_mock.set_leverage.assert_called()

    def test_03_bitget(self):
        """[Bitget] Init & Methods"""
        with patch('exchanges.bitget_exchange.ccxt') as mock_ccxt:
            ex_mock = MagicMock()
            mock_ccxt.bitget.return_value = ex_mock
            
            ex = BitgetExchange(self.config)
            self.assertTrue(ex.connect())
            
            # Balance (USDT-M)
            ex_mock.fetch_balance.return_value = {'USDT': {'free': 3000}}
            self.assertEqual(ex.get_balance(), 3000)
            
            # Price
            ex_mock.fetch_ticker.return_value = {'last': 1.5}
            self.assertEqual(ex.get_current_price(), 1.5)
            
            # Order
            ex_mock.create_order.return_value = {'id': 'bg_123'}
            self.assertEqual(ex.place_market_order('Short', 100, 1.6), 'bg_123')

    def test_04_bingx(self):
        """[BingX] Init & Methods"""
        with patch('exchanges.bingx_exchange.ccxt') as mock_ccxt:
            ex_mock = MagicMock()
            mock_ccxt.bingx.return_value = ex_mock
            
            ex = BingXExchange(self.config)
            self.assertTrue(ex.connect())
            
            # Price
            ex_mock.fetch_ticker.return_value = {'last': 100}
            self.assertEqual(ex.get_current_price(), 100)
            
            # Order
            ex_mock.create_order.return_value = {'id': 'bx_123'}
            self.assertTrue(ex.place_market_order('Long', 10, 90))

    def test_05_upbit(self):
        """[Upbit] Spot & KRW"""
        with patch('exchanges.upbit_exchange.pyupbit') as mock_upbit:
            mock_instance = MagicMock()
            mock_upbit.Upbit.return_value = mock_instance
            
            config = self.config.copy()
            config['symbol'] = 'BTC' # or KRW-BTC logic handled inside
            ex = UpbitExchange(config)
            self.assertTrue(ex.connect())
            
            # Balance
            mock_instance.get_balance.return_value = 5000000
            self.assertEqual(ex.get_balance(), 5000000)
            
            # Price
            mock_upbit.get_current_price.return_value = 100000000
            self.assertEqual(ex.get_current_price(), 100000000)
            
            # Order (Buy uses price, Sell uses volume in Upbit usually, adapter handles it)
            mock_instance.buy_market_order.return_value = {'uuid': 'up_123'}
            self.assertEqual(ex.place_market_order('Long', 0.001, 0), 'up_123')

    def test_06_bithumb(self):
        """[Bithumb] Spot & KRW"""
        with patch('exchanges.bithumb_exchange.pybithumb') as mock_pb:
            mock_instance = MagicMock()
            mock_pb.Bithumb.return_value = mock_instance
            
            ex = BithumbExchange(self.config)
            self.assertTrue(ex.connect())
            
            # Balance
            # safe_float used in adapter, checks total/free
            mock_instance.get_balance.return_value = [1000, 1000, 500, 500] # example tuple return
            self.assertGreaterEqual(ex.get_balance(), 0)
            
            # Price
            mock_pb.get_current_price.return_value = 50000000
            self.assertEqual(ex.get_current_price(), 50000000)
            
            # Order
            mock_instance.buy_market_order.return_value = ('success', '123', 'order_id_1')
            self.assertIsNotNone(ex.place_market_order('Long', 0.001, 0))

if __name__ == '__main__':
    unittest.main()
