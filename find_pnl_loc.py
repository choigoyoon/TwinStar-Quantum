from pathlib import Path
import re

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

print("PnL % 계산 위치:")
print("=" * 60)

for i, line in enumerate(lines):
    # PnL 퍼센트 계산
    if re.search(r'pnl.*%|profit.*pct|수익.*률', line, re.I):
        print(f"L{i+1}: {line.strip()}")
    
    # STATUS 로그
    elif 'STATUS' in line and 'PnL' in line:
        print(f"L{i+1}: {line.strip()}")
    
    # SL HIT 로그
    elif 'SL HIT' in line or 'SL_HIT' in line:
        print(f"L{i+1}: {line.strip()}")
