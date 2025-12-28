from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

# L3060 주변 확인
print("L3055-3070 코드:")
print("=" * 50)
for i in range(3054, 3071):
    if i < len(lines):
        print(f"{i+1}: {lines[i]}")

# Signal 클래스 정의 찾기
print("\n\nSignal 클래스/타입:")
for i, line in enumerate(lines):
    if 'class Signal' in line or 'Signal = ' in line or 'namedtuple' in line and 'Signal' in line:
        print(f"L{i+1}: {line.strip()}")
