
import sys
import unittest
from unittest.mock import MagicMock
sys.path.insert(0, rstr(Path(__file__).parent))

from core.bot_state import BotStateManager
from core.position_manager import PositionManager

class TestPositionFiltering(unittest.TestCase):
    def setUp(self):
        # 1. Setup State Manager
        self.state_mgr = BotStateManager('test', 'BTCUSDT', storage_dir='test_storage')
        # Clear previous state
        if self.state_mgr.state_file.exists():
            import os
            os.remove(self.state_mgr.state_file)
        self.state_mgr.managed_positions = {} # Reset in memory

        # 2. Setup Mock Exchange
        self.exchange = MagicMock()
        self.exchange.name = 'test'
        self.exchange.symbol = 'BTCUSDT'
        self.exchange.get_positions.return_value = [
            {'symbol': 'BTCUSDT', 'size': 1.0, 'side': 'Buy', 'entry_price': 50000}, # External
            {'symbol': 'ETHUSDT', 'size': 5.0, 'side': 'Sell', 'entry_price': 3000}  # Other symbol
        ]

        # 3. Setup Position Manager with State Manager
        self.pos_mgr = PositionManager(
            exchange=self.exchange,
            strategy_params={},
            state_manager=self.state_mgr
        )

    def test_filtering_external_position(self):
        """Test that external positions are filtered out"""
        # Initially, no managed positions
        self.assertFalse(self.state_mgr.is_managed_position('BTCUSDT'))

        # Sync
        result = self.pos_mgr.sync_with_exchange(None, {})
        
        # Should be filtered out, so 'synced' is True (empty lists match) or None action
        # If filtered out, my_positions is empty. 
        # If bot has no position, valid sync.
        
        # Verify internally (difficult without spying). 
        # But we can check if it returns "RESTORE" action.
        # If filtered out, it shouldn't see any position on exchange, so action is NONE (both empty)
        
        print(f"Result Action: {result['action']}")
        self.assertEqual(result['action'], 'NONE', "Should ignore external position")

    def test_tracking_managed_position(self):
        """Test that managed positions are tracked"""
        # Register managed position
        self.state_mgr.add_managed_position(
            'BTCUSDT', '123', 'TWIN_123', 50000, 'Long', 1.0
        )
        self.assertTrue(self.state_mgr.is_managed_position('BTCUSDT'))

        # Sync
        result = self.pos_mgr.sync_with_exchange(None, {'position': 'Long'})
        
        # Now it should see the position on exchange AND it is managed.
        # So has_exchange_position=True, has_bot_position=True
        # Action should be NONE (synced)
        
        print(f"Result Action: {result['action']}")
        self.assertEqual(result['action'], 'NONE', "Should recognize managed position")

    def tearDown(self):
        import shutil
        if self.state_mgr.storage_dir.exists() and 'test_storage' in str(self.state_mgr.storage_dir):
            shutil.rmtree(self.state_mgr.storage_dir)

if __name__ == '__main__':
    unittest.main()
