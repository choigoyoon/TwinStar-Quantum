from pathlib import Path
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

# 1. Bybit positionIdx 현황
print("[1] Bybit 주문 코드:")
bybit = base / 'exchanges/bybit_exchange.py'
if bybit.exists():
    code = bybit.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    for i, line in enumerate(lines):
        if 'order/create' in line or 'place_order' in line or 'positionIdx' in line or 'create_order' in line:
            print(f"  L{i+1}: {line.strip()[:80]}")
else:
    print("  ❌ bybit_exchange.py not found")

# 2. Signal.get() 잔여 확인
print("\n[2] Signal.get() 잔여:")
bot = base / 'core/unified_bot.py'
if bot.exists():
    code2 = bot.read_text(encoding='utf-8', errors='ignore')
    lines2 = code2.split('\n')
    for i, line in enumerate(lines2):
        if 'signal.get(' in line.lower() or "signal['direction']" in line or "signal['type']" in line:
            print(f"  L{i+1}: {line.strip()[:80]}")
else:
    print("  ❌ unified_bot.py not found")
