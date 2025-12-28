import os

# unified_bot.py ATR/SL 검색
path = r'C:\매매전략\core\unified_bot.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('=== unified_bot: ATR 기반 SL 계산 ===')
for i, line in enumerate(lines):
    if 'atr' in line.lower() and ('sl' in line.lower() or 'stop' in line.lower()):
        start = max(0, i-2)
        end = min(len(lines), i+3)
        for j in range(start, end):
            print(f'L{j+1}: {lines[j].rstrip()[:90]}')
        print('---')

# strategy_core.py ATR/SL 검색
path2 = r'C:\매매전략\core\strategy_core.py'
with open(path2, 'r', encoding='utf-8') as f:
    lines2 = f.readlines()

print('\n=== strategy_core: ATR_mult/SL 계산 ===')
for i, line in enumerate(lines2):
    if 'atr_mult' in line.lower() or 'stop_loss' in line.lower():
        if '=' in line or '*' in line:
            print(f'L{i+1}: {line.strip()[:90]}')
