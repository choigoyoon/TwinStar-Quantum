from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

# 1. bybit_exchange.py에서 110043 처리
print("[1] bybit_exchange.py 110043 처리:")
bybit = base / 'exchanges/bybit_exchange.py'
code = bybit.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

for i, line in enumerate(lines):
    if '110043' in line:
        print(f"  L{i+1}: {line.strip()}")

# 2. unified_bot.py에서 레버리지 실패 처리
print("\n[2] unified_bot.py 레버리지 실패 처리:")
bot = base / 'core/unified_bot.py'
code2 = bot.read_text(encoding='utf-8', errors='ignore')
lines2 = code2.split('\n')

for i, line in enumerate(lines2):
    if 'Leverage' in line and 'failed' in line.lower():
        # 주변 5줄 출력
        for j in range(max(0, i-2), min(len(lines2), i+3)):
            print(f"  L{j+1}: {lines2[j].strip()[:60]}")
        print()
