import os

# 1. unified_bot.py 캔들 마감 처리
path = r'C:\매매전략\core\unified_bot.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('=== unified_bot: 캔들 마감 처리 ===')
for i, line in enumerate(lines):
    if 'candle_close' in line.lower() or 'on_candle' in line.lower():
        print(f'L{i+1}: {line.strip()[:90]}')

# 2. ws_handler.py 캔들 처리
path2 = r'C:\매매전략\exchanges\ws_handler.py'
with open(path2, 'r', encoding='utf-8') as f:
    lines2 = f.readlines()

print('\n=== ws_handler: 캔들 확정 체크 ===')
for i, line in enumerate(lines2):
    if 'confirm' in line.lower() or 'closed' in line.lower() or 'final' in line.lower():
        print(f'L{i+1}: {line.strip()[:80]}')

print('\n=== ws_handler: kline 처리 로직 ===')
for i, line in enumerate(lines2):
    if 'kline' in line.lower() and ('=' in line or 'def ' in line):
        start = max(0, i-1)
        end = min(len(lines2), i+4)
        for j in range(start, end):
            print(f'L{j+1}: {lines2[j].rstrip()[:90]}')
        print('---')
