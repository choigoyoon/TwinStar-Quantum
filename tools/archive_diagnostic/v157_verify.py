from pathlib import Path
import re

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

print('=== [1] 백테스트 PnL 계산 ===')
for i, line in enumerate(lines):
    if 'backtest' in line.lower() and 'pnl' in line.lower():
        print(f'L{i+1}: {line.strip()[:100]}')

print('\n=== [2] 실전매매 PnL (execute/close) ===')
for i, line in enumerate(lines):
    if ('_execute' in line or '_close' in line) and 'pnl' in line.lower():
        print(f'L{i+1}: {line.strip()[:100]}')

print('\n=== [3] 복리 계산 (compound/capital) ===')
for i, line in enumerate(lines):
    if 'compound' in line.lower() or 'capital' in line.lower():
        if 'pnl' in line.lower() or 'seed' in line.lower():
            print(f'L{i+1}: {line.strip()[:100]}')

print('\n=== [4] 레버리지 적용 여부 ===')
for i, line in enumerate(lines):
    # pnl_pct = ... 형식 찾기
    if re.search(r'pnl_pct\s*=', line):
        # 제외: 초기값 할당 (pnl_pct = 0 등)
        if re.search(r'=\s*[0-9]', line):
             continue
        has_lev = 'leverage' in line.lower()
        mark = '✅' if has_lev else '❌'
        print(f'{mark} L{i+1}: {line.strip()[:100]}')

print('\n=== [5] bt_state 정리 여부 ===')
for i, line in enumerate(lines):
    if "bt_state['position']" in line and '= None' in line:
        print(f'✅ L{i+1}: {line.strip()}')
