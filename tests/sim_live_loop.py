import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
import sys
import shutil
from pathlib import Path
from datetime import datetime, timedelta

# Add project root
sys.path.insert(0, str(Path(rstr(Path(__file__).parent))))

from core.unified_bot import UnifiedBot

class TestLiveLoop(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/temp_sim_test")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch('core.unified_bot.UnifiedBot.save_state')
    def test_live_data_flow(self, mock_save):
        """Simulate a sequence of candle updates and verify flow"""
        
        # 1. Mock Exchange
        mock_exchange = MagicMock()
        mock_exchange.name = 'bybit'
        mock_exchange.symbol = 'BTC/USDT'
        
        # 2. Init Bot
        bot = UnifiedBot(exchange=mock_exchange)
        
        # Mock modules
        bot.mod_data = MagicMock()
        bot.mod_signal = MagicMock()
        bot.mod_order = MagicMock()
        bot.mod_position = MagicMock()
        
        # 3. Simulate Candle Closes (1h sequence)
        start_time = datetime(2024, 1, 1, 10, 0, 0)
        
        print("\n[SIM] Feeding 10 candles...")
        for i in range(10):
            current_time = start_time + timedelta(hours=i)
            candle = {
                'timestamp': current_time,
                'open': 100 + i, 'high': 105 + i, 'low': 95 + i, 'close': 102 + i,
                'volume': 1000
            }
            
            # Inject Event
            bot._on_candle_close(candle)
            
            # Verify Flow
            # 1. Data appended?
            bot.mod_data.append_candle.assert_called_with(candle)
            
            # 2. Historical processed? (Actually _process_historical_data calls mod_data logic)
            # Check if internal processing triggered
            # In UnifiedBot._on_candle_close:
            #   self.mod_data.append_candle(candle)
            #   self._process_historical_data() -> this calls self.mod_data.process_data() usually, 
            #   but _process_historical_data is a method on bot.
            
            # 3. Signal Check?
            # mod_signal.add_patterns_from_df is called in _on_candle_close
            bot.mod_signal.add_patterns_from_df.assert_called()
            
            # Reset mocks for next loop
            bot.mod_data.reset_mock()
            bot.mod_signal.reset_mock()
        
        print("[SIM] Candle flow verified.")
        
        # 4. Simulate Price Update (Live Position Management)
        bot.position = {'side': 'Long', 'entry_price': 100, 'size': 1}
        price = 110.0 # Profit
        
        # Mock position manager decision
        bot.mod_position.manage_live.return_value = {'action': 'CLOSE', 'reason': 'TP'}
        bot.mod_order.execute_close.return_value = True
        
        print("[SIM] Feeding Price Update (TP Hit)...")
        bot._on_price_update(price)
        
        # Verify Close Triggered
        bot.mod_position.manage_live.assert_called()
        bot.mod_order.execute_close.assert_called()
        print("[SIM] Position Close logic verified.")

if __name__ == '__main__':
    unittest.main()
