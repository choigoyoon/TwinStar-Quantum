import os
import sys
from pathlib import Path

root_dir = Path(r"C:\매매전략")
sys.path.insert(0, str(root_dir))

from core.bot_state import BotStateManager

def test_state_persistence():
    print("\n--- BotStateManager Persistence Test ---")
    
    symbol = "BTCUSDT"
    exchange = "bybit"
    
    # Initialize manager
    manager = BotStateManager(exchange, symbol)
    state_file = manager.get_state_file_path()
    print(f"State file path: {state_file}")
    
    # 1. Create dummy state
    test_state = {
        'last_update': '2025-12-30 15:00:00',
        'position': {
            'symbol': symbol,
            'side': 'Long',
            'entry_price': 98500.0,
            'size': 0.1,
            'stop_loss': 97000.0
        },
        'managed_positions': {
            symbol: {
                'entry_price': 98500.0,
                'side': 'Long',
                'size': 0.1
            }
        },
        'capital': 10500.5
    }
    
    # 2. Save state
    print(f"Saving test state...")
    success = manager.save_state(test_state)
    if success:
        print("✅ State saved successfully.")
    else:
        print("❌ State save failed.")

    # 3. Load state
    print(f"Loading state...")
    loaded_state = manager.load_state()
    
    if loaded_state:
        print("✅ State loaded successfully.")
        # Verify specific values
        if loaded_state.get('capital') == 10500.5 and \
           loaded_state.get('position', {}).get('entry_price') == 98500.0:
            print("✅ Data integrity verified.")
        else:
            print(f"❌ Data mismatch: {loaded_state}")
    else:
        print("❌ State load returned None.")

    # 4. Managed positions helper test
    print(f"Testing managed positions helper...")
    if manager.is_managed_position(symbol):
        pos = manager.get_managed_position(symbol)
        print(f"✅ Managed position found: {pos}")
    else:
        print("❌ Managed position check failed.")

    print("\n--- Test Complete ---\n")

if __name__ == "__main__":
    test_state_persistence()
