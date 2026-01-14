
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import logging

sys.path.insert(0, rstr(Path(__file__).parent))

# MOCK MODULES
sys.modules['core.license_guard'] = MagicMock()
sys.modules['license_manager'] = MagicMock()
sys.modules['core.strategy_core'] = MagicMock()

# Mock BaseExchange Signal
mock_base_exchange = MagicMock()
class MockSignal:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.signal_type = kwargs.get('type')
        self.pattern = kwargs.get('pattern') 
mock_base_exchange.Signal = MockSignal
sys.modules['exchanges.base_exchange'] = mock_base_exchange

try:
    from core.unified_bot import UnifiedBot
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

# FORCE RE-CONFIGURE LOGGING AFTER IMPORT
root = logging.getLogger()
if root.handlers:
    for handler in root.handlers[:]:
        root.removeHandler(handler)
logging.basicConfig(filename='verify_test.log', level=logging.DEBUG, filemode='w', force=True)

class TestBotFlow(unittest.TestCase):
    def setUp(self):
        logging.info("[Setup] Instantiating UnifiedBot...")
        self.mock_exchange = MagicMock()
        self.mock_exchange.name = 'test_exchange'
        self.mock_exchange.symbol = 'BTC/USDT'
        self.mock_exchange.timeframe = '15m'
        self.mock_exchange.amount_usd = 1000
        
        # KEY FIX: Set attributes to primitive types to avoid formatting errors in logging
        self.mock_exchange.capital = 1000.0
        self.mock_exchange.leverage = 5

        self.bot = UnifiedBot(self.mock_exchange, simulation_mode=True)
        
        self.bot.bt_state = {
            'pending': [],
            'position': None,
            'positions': [],
            'last_time': pd.Timestamp.now() - timedelta(hours=1),
            'balance': 1000,
            'last_idx': 0
        }
        
        self.bot.execute_entry = MagicMock()
        self.bot.strategy_params = {'atr_mult': 1.0, 'trail_start_r': 1.0, 'trail_dist_r': 0.2}
        self.bot.ATR_MULT = 1.0
        
        self.bot._check_entry_live = MagicMock(return_value={
            'action': 'ENTRY',
            'direction': 'Long',
            'price': 50000.0,
            'sl': 49000.0,
            'pattern': 'TestPattern'
        })
        
        self.bot.indicator_cache['df_entry'] = pd.DataFrame({
            'timestamp': [pd.Timestamp.now() - timedelta(minutes=15)],
            'open': [50000], 'high': [50100], 'low': [49900], 'close': [50000], 'volume': [100]
        })
        self.bot.df_entry_full = self.bot.indicator_cache['df_entry'].copy()

    def test_websocket_collection_and_entry(self):
        logging.info("[TEST] Start")
        
        new_candle = {
            'timestamp': pd.Timestamp.now(),
            'open': 50000.0,
            'high': 50200.0,
            'low': 49800.0,
            'close': 50100.0,
            'volume': 150.0
        }
        
        logging.info("[1] Calling _process_new_candle")
        # Execute normally without wrappers now that we know the crash cause
        try:
            self.bot._process_new_candle(new_candle)
        except Exception as e:
            logging.exception("Exception in _process_new_candle")

        logging.info("[2] Checking Results")
        
        # Verify Data Collection
        col_success = False
        df = self.bot.indicator_cache['df_entry']
        if len(df) == 2:
            logging.info("  ✅ Data Collection Success (Length=2)")
            col_success = True
        else:
            logging.error(f"  ❌ Data Collection Failed (Length={len(df)})")

        # Verify Execution
        exec_success = False
        if self.bot.execute_entry.called:
             args = self.bot.execute_entry.call_args[0][0]
             logging.info(f"  ✅ execute_entry called with {args.signal_type}")
             exec_success = True
        else:
             logging.error("  ❌ execute_entry NOT called")

        if col_success and exec_success:
            print("\n✅ Verification SUCCESS: WS Data & Entry Command confirmed.")
        else:
            print("\n❌ Verification FAILED.")
            self.fail("Verification Failed")

if __name__ == '__main__':
    unittest.main()
