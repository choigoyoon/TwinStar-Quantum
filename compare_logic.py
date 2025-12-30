from pathlib import Path

base = Path(r'C:\매매전략')

print('=== 최적화 vs 백테스트 로직 비교 ===')

# 1) 최적화 계산 로직
opt_file = base / 'GUI' / 'optimization_widget.py'
if opt_file.exists():
    code = opt_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print('\n[1] 최적화 - 승률/수익률 계산:')
    for i, line in enumerate(lines):
        if 'win' in line.lower() and 'rate' in line.lower():
            print(f'  L{i+1}: {line.strip()[:100]}') # Increased line length for more context
        if 'pnl' in line.lower() and '=' in line:
            print(f'  L{i+1}: {line.strip()[:100]}')

# 2) 백테스트 계산 로직
bt_file = base / 'GUI' / 'backtest_widget.py'
if bt_file.exists():
    code = bt_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print('\n[2] 백테스트 - 승률/수익률 계산:')
    for i, line in enumerate(lines):
        if 'win' in line.lower() and 'rate' in line.lower():
            print(f'  L{i+1}: {line.strip()[:100]}')
        if 'pnl' in line.lower() and '=' in line:
            print(f'  L{i+1}: {line.strip()[:100]}')

# 3) 코어 전략 계산
core_file = base / 'core' / 'strategy_core.py'
if core_file.exists():
    code = core_file.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print('\n[3] 코어 - 백테스트 함수:')
    for i, line in enumerate(lines):
        if 'def ' in line and 'backtest' in line.lower():
            print(f'  L{i+1}: {line.strip()}')

print('\n=== 완료 ===')
