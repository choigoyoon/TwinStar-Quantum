import os

# 1. optimization_widget.py Manual Settings 내부
print('=== optimization_widget.py Manual Settings 내부 ===')
with open('GUI/optimization_widget.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if 'Manual' in line or 'ATR' in line or 'Trail' in line or 'Min' in line or 'Max' in line or 'Step' in line:
            if 't(' not in line and ('Label' in line or 'setText' in line or 'QLabel' in line):
                print(f'L{i+1}: {line.strip()[:60]}')

# 2. results_widget.py / history_widget.py 영어 텍스트
print('\n=== history_widget.py / backtest_result_widget.py 영어 텍스트 ===')
for fname in ['history_widget.py', 'backtest_result_widget.py']:
    path = f'GUI/{fname}'
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        print(f'\n--- {fname} ---')
        count = 0
        for i, line in enumerate(lines):
            if 't(' not in line:
                keywords = ['Total', 'Win', 'Trade', 'Profit', 'Loss', 'Best', 'Worst', 'Max', 'Avg', 'Drawdown', 'Factor', 'Streak', 'Rate', 'Capital']
                for kw in keywords:
                    if kw in line and ('create_stat_card' in line or '"' in line):
                        print(f'L{i+1}: {line.strip()[:60]}')
                        count += 1
                        if count > 10:
                            break
                        break

# 3. 결과 탭 카드 텍스트
print('\n=== 결과 탭 카드 텍스트 ===')
with open('GUI/history_widget.py', 'r', encoding='utf-8') as f:
    content = f.read()
targets = ['Total Trades', 'Win Rate', 'Total PnL', 'Profit Factor', 'Avg PnL', 
           'Max Drawdown', 'Best Trade', 'Worst Trade', 'Max Win Streak', 
           'Max Lose Streak', 'BE Trigger', 'Current Capital']
for t in targets:
    if t in content:
        print(f'발견: {t}')
