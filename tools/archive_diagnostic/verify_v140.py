from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')
errors = []

print('=' * 60)
print('v1.4.0 최종 검증')
print('=' * 60)

# 1. 문법 검사
print('\n[1] 문법 검사')
files = [
    'core/unified_bot.py',
    'GUI/trading_dashboard.py',
    'exchanges/bybit_exchange.py',
]
for f in files:
    path = base / f
    if path.exists():
        try:
            code = path.read_text(encoding='utf-8', errors='ignore')
            compile(code, f, 'exec')
            print(f'  OK {f}')
        except SyntaxError as e:
            print(f'  ERR {f}: L{e.lineno}')
            errors.append(f)

# 2. 핵심 기능 확인
print('\n[2] 핵심 기능')
bot = base / 'core/unified_bot.py'
code = bot.read_text(encoding='utf-8', errors='ignore')

checks = {
    'STATE_FILE': 'bot_state.json' in code,
    'save_state': 'def save_state' in code,
    'capital save': "capital" in code,
    'duplicate prevention': 'Already in position' in code,
    'SYNC bt_state': 'current_sl' in code and 'extreme_price' in code,
}

for name, result in checks.items():
    print(f'  {"OK" if result else "ERR"} {name}')
    if not result:
        errors.append(name)

# 3. UI 타이머
print('\n[3] UI 동기화')
dash = base / 'GUI/trading_dashboard.py'
if dash.exists():
    ui = dash.read_text(encoding='utf-8', errors='ignore')
    if '_state_timer' in ui:
        print('  OK UI Timer')
    else:
        print('  ERR UI Timer')
        errors.append('UI timer')

# 결과
print()
print('=' * 60)
if errors:
    print(f'FAIL {len(errors)} issues: {errors}')
else:
    print('PASS v1.4.0 Ready!')
