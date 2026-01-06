import os

files = [
    'GUI/trading_dashboard.py',
    'GUI/optimization_widget.py', 
    'GUI/backtest_widget.py', 
    'core/unified_bot.py',
    'GUI/staru_main.py'
]

print(f"{'File':<40} Lines")
print('-'*50)
for f in files:
    path = os.path.join('C:/매매전략', f)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
            print(f"{f:<40} {len(fp.readlines())}")
    else:
        print(f"{f:<40} Not Found")
