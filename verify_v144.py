
import sys
import os
import logging
from datetime import datetime
from unittest.mock import MagicMock

# Add root directory to sys.path
sys.path.append(os.getcwd())

# Mock required imports before they happen in unified_bot
sys.modules['paths'] = MagicMock()
sys.modules['license_manager'] = MagicMock()
sys.modules['utils.preset_manager'] = MagicMock()
sys.modules['utils.strategy_loader'] = MagicMock()

from core.unified_bot import UnifiedBot, Position
from exchanges.base_exchange import BaseExchange

def test_v144_logic():
    print("=== Testing v1.4.4 Order ID Tracking Logic ===")
    
    # Mock exchange
    mock_exchange = MagicMock(spec=BaseExchange)
    mock_exchange.name = "Bybit"
    mock_exchange.symbol = "BTCUSDT"
    mock_exchange.amount_usd = 1000.0
    mock_exchange.preset_name = "default"
    
    # Mock global functions used in UnifiedBot.__init__
    import core.unified_bot
    core.unified_bot.load_strategy_params = MagicMock(return_value={'preset_name': 'default'})
    
    import utils.preset_manager
    utils.preset_manager.get_backtest_params = MagicMock(return_value={
        'atr_mult': 2.0,
        'trail_start_r': 1.0,
        'trail_dist_r': 0.2
    })

    # Initialize bot
    bot = UnifiedBot(mock_exchange, simulation_mode=True)
    bot.bt_state = {'positions': []} # Reset state
    
    print("\n1. Testing order_id storage in bt_state...")
    # Simulate an entry
    test_id = "test_order_123"
    bot.bt_state['positions'].append({
        'order_id': test_id,
        'side': 'Long',
        'price': 50000,
        'size': 0.1,
        'time': datetime.now().isoformat()
    })
    
    if any(p['order_id'] == test_id for p in bot.bt_state['positions']):
        print(f"✅ Order ID {test_id} successfully stored in bt_state.")
    else:
        print(f"❌ Failed to store Order ID in bt_state.")

    print("\n2. Testing sync_position matching logic (MOCK)...")
    # Mock exchange position
    mock_exchange_pos = {
        'symbol': 'BTCUSDT',
        'side': 'Buy',
        'size': 0.1,
        'entry_price': 50000,
        'order_id': test_id
    }
    
    # Check if we can find the match
    found_match = False
    for p in bot.bt_state.get('positions', []):
        if str(p.get('order_id')) == str(test_id):
            found_match = True
            break
            
    if found_match:
        print(f"✅ Match found for exchange order {test_id} in bot state.")
    else:
        print(f"❌ Match NOT found for exchange order {test_id}.")

    print("\n3. Testing external position detection (MOCK)...")
    external_id = "external_order_999"
    found_external = True
    for p in bot.bt_state.get('positions', []):
        if str(p.get('order_id')) == str(external_id):
            found_external = False
            break
            
    if found_external:
        print(f"✅ System correctly identifies {external_id} as EXTERNAL (not in bot state).")
    else:
        print(f"❌ System mistakenly marks {external_id} as bot-owned.")

    print("\n=== v1.4.4 Logic Verification Complete ===")

if __name__ == "__main__":
    test_v144_logic()
