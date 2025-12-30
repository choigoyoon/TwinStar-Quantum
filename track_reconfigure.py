from pathlib import Path

base = Path(r'C:\매매전략')

print('=== reconfigure 에러 추적 ===\n')

# [1] reconfigure 호출 위치
print('[1] reconfigure 호출 위치:')
for f in base.rglob('*.py'):
    if any(p in str(f) for p in ['__pycache__', '.venv', 'build', 'dist']):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        if 'reconfigure' in code:
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if 'reconfigure' in line:
                    print(f'  {f.relative_to(base)} L{i+1}: {line.strip()[:70]}')
    except:
        pass

# [2] logging 설정 위치
print('\n[2] logging 설정:')
files_to_check = [
    base / 'GUI' / 'trading_dashboard.py',
    base / 'GUI' / 'staru_main.py',
    base / 'core' / 'unified_bot.py',
    base / 'core' / 'strategy_core.py'
]

for f in files_to_check:
    if f.exists():
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if 'logging' in line and ('getLogger' in line or 'basicConfig' in line or 'handler' in line.lower()):
                print(f'  {f.name} L{i+1}: {line.strip()[:70]}')

# [3] logger 변수 확인 (TradingDashboard 위주)
print('\n[3] logger 변수 확인 (trading_dashboard.py):')
f = base / 'GUI' / 'trading_dashboard.py'
if f.exists():
    code = f.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    for i, line in enumerate(lines):
        if ('logger' in line.lower() or 'log' in line.lower()) and '=' in line and len(line.strip()) < 100:
             # Filter out common false positives like "login"
             if not any(x in line for x in ['login', 'logic']):
                print(f'  L{i+1}: {line.strip()[:70]}')
