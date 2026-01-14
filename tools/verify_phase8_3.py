
import sys
import unittest
import time
from unittest.mock import MagicMock
from datetime import datetime

sys.path.insert(0, rstr(Path(__file__).parent))
from core.order_executor import OrderExecutor
from core.bot_state import BotStateManager

class TestProfitTracking(unittest.TestCase):
    def setUp(self):
        # 1. Setup Mock Exchange
        self.exchange = MagicMock()
        self.exchange.name = 'test'
        self.exchange.symbol = 'BTCUSDT'
        self.exchange.leverage = 10
        self.exchange.dry_run = False
        self.exchange.close_position.return_value = True
        self.exchange.get_trade_history.return_value = [
            {
                'timestamp': int(time.time() * 1000) + 100, # slightly future/now
                'side': 'Sell',
                'price': 51000.0,
                'size': 1.0,
                'fee': 5.0,
                'realized_pnl': 1000.0, # 51000 - 50000 = 1000
                'order_id': 'real_ord_123'
            }
        ]

        # 2. Setup State Manager
        self.state_mgr = MagicMock(spec=BotStateManager)
        
        # 3. Setup Order Executor
        self.executor = OrderExecutor(
            exchange=self.exchange,
            strategy_params={'slippage': 0.0006},
            state_manager=self.state_mgr,
            dry_run=False
        )

    def test_close_with_real_pnl(self):
        """Test close execution uses real PnL from history"""
        # Mock Position
        position = MagicMock()
        position.entry_price = 50000.0
        position.side = 'Long'
        position.size = 1.0
        position.entry_time = None
        
        # Execute Close
        result = self.executor.execute_close(position, exit_price=51000.0, reason="Test")
        
        # Verify
        self.assertIsNotNone(result)
        self.assertTrue(result['real_history'])
        self.assertEqual(result['pnl_usd'], 1000.0)
        self.assertEqual(result['fee'], 5.0)
        self.assertEqual(result['exchange_order_id'], 'real_ord_123')
        
        # Verify save_trade called
        self.state_mgr.save_trade.assert_called_once()
        saved_trade = self.state_mgr.save_trade.call_args[0][0]
        self.assertEqual(saved_trade['pnl_usd'], 1000.0)
        
        # Verify managed position removed
        self.state_mgr.remove_managed_position.assert_called_with('BTCUSDT')

    def test_close_fallback_pnl(self):
        """Test fallback when history not found"""
        self.exchange.get_trade_history.return_value = [] # Empty
        
        position = MagicMock()
        position.entry_price = 50000.0
        position.side = 'Long'
        position.size = 1.0
        
        result = self.executor.execute_close(position, exit_price=51000.0, reason="Fallback")
        
        self.assertFalse(result['real_history'])
        # Calculated PnL: (51000 - 50000) - fee
        # Fee = 1*50000*0.0006 + 1*51000*0.0006 ~= 30 + 30.6 = 60.6
        # PnL ~= 1000 - 60.6 = 939.4
        self.assertAlmostEqual(result['pnl_usd'], 939.4, delta=1.0)

if __name__ == '__main__':
    unittest.main()
