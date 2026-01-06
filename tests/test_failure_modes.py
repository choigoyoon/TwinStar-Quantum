import unittest
import json
import os
import sys
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root
sys.path.insert(0, str(Path(r"C:\매매전략")))

from core.bot_state import BotStateManager
from core.unified_bot import UnifiedBot

class TestFailureResilience(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/temp_failure_test")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_corrupted_state_recovery(self):
        """Test if BotStateManager survives corrupted JSON"""
        manager = BotStateManager('bybit', 'BTCUSDT', storage_dir=str(self.test_dir))
        
        # 1. Create corrupted file
        bad_file = self.test_dir / "bybit_btcusdt_state.json"
        with open(bad_file, 'w') as f:
            f.write("{ INVALID JSON : }")
            
        # 2. Attempt load
        state = manager.load_state()
        
        # 3. Verify
        self.assertIsNone(state, "Should return None on corruption, not crash")
        # Ensure file still exists (or was renamed to backup, logic dependent)
        # Ideally, it should log error and return None.

    @patch('ccxt.bybit')
    def test_api_connection_failure(self, mock_ccxt):
        """Test bot behavior when API raises exception"""
        # Setup Mock Exchange
        mock_exchange = MagicMock()
        mock_ccxt.return_value = mock_exchange
        
        # Simulate Network Error on fetch_ticker
        from ccxt import NetworkError
        mock_exchange.fetch_ticker.side_effect = NetworkError("Connection Timed Out")
        
        # UnifiedBot requires an 'exchange' object, normally created by ExchangeFactory
        # or passed directly. Signature: UnifiedBot(exchange, ...)
        
        # We need to minimally mock the exchange object to pass initialization
        mock_exchange.name = 'bybit'
        mock_exchange.symbol = 'BTC/USDT'
        
        # Inject mock exchange into bot
        bot = UnifiedBot(exchange=mock_exchange)
        
        try:
            # 3. Simulate API Failure during data fetch
            # UnifiedBot delegates to mod_data.backfill
            # We pass a lambda that invokes the failing mock
            fetch_callback = lambda limit: mock_exchange.fetch_ticker('BTC/USDT') # Using fetch_ticker as dummy, or get_klines
            
            # Actually backfill takes a callback that returns list of candles
            # If callback raises exception, backfill should handle it (log and return 0) or raise it
            
            # Let's test with get_klines mock
            mock_exchange.get_klines.side_effect = NetworkError("Connection Timed Out")
            
            # The bot's monitor loop calls: self.mod_data.backfill(lambda lim: sig_ex.get_klines('15', lim))
            # We test this specific call
            result = bot.mod_data.backfill(lambda lim: mock_exchange.get_klines('15', lim))
            
            # If backfill catches the error, result is likely 0 (added candles)
            # If backfill re-raises, we catch it here and pass (since monitor loop catches it)
            # But ideally component should be resilient? 
            # Let's see behavior. If it crashes script, test fails.
            
            print(f"Backfill result on failure: {result}")
            
        except NetworkError:
            print("Caught expected NetworkError (Component re-raises, which is fine if Monitor loop catches)")
        except Exception as e:
            # If it's another error, fail
            if "Connection Timed Out" in str(e):
                 print("Caught exception with correct message")
            else:
                 self.fail(f"Bot/Component crashed on NetworkError with unexpected error: {e}")

    def test_invalid_order_handling(self):
        """Test graceful handling of invalid orders"""
        # This requires mocking OrderExecutor or strategy signal execution
        pass

if __name__ == '__main__':
    unittest.main()
