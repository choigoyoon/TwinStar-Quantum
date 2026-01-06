import os

# 1. unified_bot.py SL 체크 로직
path = r'C:\매매전략\core\unified_bot.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('=== unified_bot: SL 체크/히트 로직 ===')
for i, line in enumerate(lines):
    if 'stop_loss' in line.lower() or 'sl_price' in line.lower():
        if 'check' in line.lower() or '<' in line or '>' in line or 'close' in line.lower():
            start = max(0, i-2)
            end = min(len(lines), i+3)
            for j in range(start, end):
                print(f'L{j+1}: {lines[j].rstrip()[:90]}')
            print('---')

# 2. close_position 로직
print('\n=== unified_bot: close_position 호출 ===')
count = 0
for i, line in enumerate(lines):
    if 'close_position' in line.lower():
        print(f'L{i+1}: {line.strip()[:90]}')
        count += 1
        if count >= 10:
            break

# 3. 거래소 SL 주문 방식
path2 = r'C:\매매전략\exchanges\bybit_exchange.py'
with open(path2, 'r', encoding='utf-8') as f:
    lines2 = f.readlines()

print('\n=== bybit_exchange: SL 주문 방식 ===')
for i, line in enumerate(lines2):
    if 'stop' in line.lower() and ('order' in line.lower() or 'loss' in line.lower()):
        print(f'L{i+1}: {line.strip()[:90]}')
