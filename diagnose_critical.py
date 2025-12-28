from pathlib import Path
import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print("=" * 70)
print("크래시 유발 핵심 패턴만 검사")
print("=" * 70)

critical = []

# 핵심 파일만
core_files = [
    'core/unified_bot.py',
    'core/strategy_core.py',
    'exchanges/bybit_exchange.py',
    'exchanges/binance_exchange.py',
    'exchanges/ws_handler.py',
]

for cf in core_files:
    f = base / cf
    if not f.exists():
        continue
    
    code = f.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print(f"\n[{cf}]")
    
    for i, line in enumerate(lines):
        # 1. order/result/response.get() - bool일 수 있음
        if re.search(r'(order|result|response|position|trade)\.get\(', line):
            prev = '\n'.join(lines[max(0,i-3):i+1])
            if 'isinstance' not in prev and 'if ' not in prev:
                critical.append((cf, i+1, line.strip()[:60]))
                print(f"  L{i+1}: {line.strip()[:55]}")
        
        # 2. signal.get() - Signal 객체일 수 있음
        if 'signal.get(' in line.lower():
            critical.append((cf, i+1, line.strip()[:60]))
            print(f"  L{i+1}: {line.strip()[:55]}")
        
        # 3. df['column'] - KeyError 위험 (df.get 아님)
        if re.search(r"df\[['\"](?!timestamp|close|open|high|low)", line):
            if '.get(' not in line and 'try' not in '\n'.join(lines[max(0,i-2):i]):
                pass  # DataFrame은 나중에

print("\n" + "=" * 70)
print(f"크래시 유발 핵심: {len(critical)}개")
print("=" * 70)

if critical:
    print("\n이것들만 수정하면 됨:")
    for cf, ln, code in critical:
        print(f"  {cf} L{ln}")
