import sys
import os

sys.path.insert(0, os.getcwd())

try:
    from config.parameters import DEFAULT_PARAMS
    print('=== Dry-run Config Check ===')
    print(f'Symbol: BTCUSDT')
    print(f'Exchange: Bybit')
    print(f"Leverage: {DEFAULT_PARAMS.get('leverage', 10)}")
    print(f"ATR mult: {DEFAULT_PARAMS.get('atr_mult', 2.2)}")
    print('Config OK')
except Exception as e:
    print(f'Config Check Failed: {e}')
