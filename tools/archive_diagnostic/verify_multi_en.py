"""Multi-trader/sniper verification"""
import os
import sys
sys.path.insert(0, rstr(Path(__file__).parent))

print("=" * 50)
print("Multi-Trader/Sniper Verification")
print("=" * 50)

# 1. Module Import
print("\n[1] Module Import")
print("-" * 40)

try:
    from core.multi_trader import MultiTrader, CoinStatus, CoinState
    print("OK: core.multi_trader")
except Exception as e:
    print(f"ERR: core.multi_trader - {e}")

try:
    from core.multi_sniper import MultiCoinSniper
    print("OK: core.multi_sniper")
except Exception as e:
    print(f"ERR: core.multi_sniper - {e}")

# 2. GUI files
print("\n[2] GUI Components")
print("-" * 40)

gui_files = ['GUI/multi_session_popup.py', 'GUI/sniper_session_popup.py']
for f in gui_files:
    status = "OK" if os.path.exists(f) else "MISSING"
    print(f"{status}: {f}")

# 3. MultiTrader methods
print("\n[3] MultiTrader Methods")
print("-" * 40)

with open('core/multi_trader.py', 'r', encoding='utf-8') as f:
    content = f.read()

methods = ['def initialize', 'def start_websocket', 'rotate_subscriptions',
           '_load_all_optimized_coins', '_on_bybit_kline', '_try_entry',
           '_execute_order', '_manage_position']

for m in methods:
    status = "OK" if m in content else "MISSING"
    print(f"{status}: {m}")

# 4. MultiSniper methods
print("\n[4] MultiSniper Methods")
print("-" * 40)

with open('core/multi_sniper.py', 'r', encoding='utf-8') as f:
    content2 = f.read()

methods2 = ['def initialize', '_get_top50_by_volume', '_calc_readiness',
            '_analyze_pattern', '_try_entry', '_execute_order',
            '_check_exit_condition', '_execute_exit']

for m in methods2:
    status = "OK" if m in content2 else "MISSING"
    print(f"{status}: {m}")

# 5. Exchange support
print("\n[5] Exchange Support")
print("-" * 40)

for ex in ['bybit', 'binance', 'okx', 'bitget']:
    if ex in content.lower() or ex in content2.lower():
        print(f"OK: {ex}")
    else:
        print(f"WARN: {ex} not found")

# 6. WebSocket
print("\n[6] WebSocket")
print("-" * 40)

for p in ['_start_bybit_ws', '_start_binance_ws', '_subscribe_ws']:
    status = "OK" if p in content else "MISSING"
    print(f"{status}: {p}")

# 7. Issues
print("\n[7] Potential Issues")
print("-" * 40)

if 'NotImplemented' in content:
    print("WARN: NotImplemented found")
if 'pass  # TODO' in content:
    print("WARN: TODO found")
if 'exchange_client' in content:
    print("OK: exchange_client")
else:
    print("WARN: exchange_client missing")

print("\n" + "=" * 50)
print("Verification Complete")
print("=" * 50)
