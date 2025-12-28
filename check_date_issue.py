"""1970-01-01 날짜 오류 원인 분석"""
import os

# 1. strategy_core.py 타임스탬프 처리
path = r'C:\매매전략\core\strategy_core.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('=== strategy_core: 날짜/타임스탬프 처리 ===')
for i, line in enumerate(lines):
    if 'timestamp' in line.lower() or 'entry_time' in line or 'exit_time' in line:
        if '=' in line or 'append' in line:
            print(f'L{i+1}: {line.strip()[:90]}')

# 2. backtest_widget.py 날짜 표시
path2 = r'C:\매매전략\GUI\backtest_widget.py'
with open(path2, 'r', encoding='utf-8') as f:
    lines2 = f.readlines()

print('\n=== backtest_widget: 날짜 표시 ===')
for i, line in enumerate(lines2):
    if 'entry_time' in line.lower() or 'exit_time' in line.lower() or 'strftime' in line:
        print(f'L{i+1}: {line.strip()[:90]}')
