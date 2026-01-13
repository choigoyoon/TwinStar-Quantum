from pathlib import Path
import ast
import sys

base = Path(r'C:\매매전략')

print('=== 빌드 전 Import 검증 ===\n')

errors = []

# [1] 문법 검사
print('[1] 문법 검사...')
for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or '.venv' in str(f) or 'build' in str(f) or 'dist' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        ast.parse(code)
    except SyntaxError as e:
        errors.append(f'❌ 문법: {f.relative_to(base)} L{e.lineno}: {e.msg}')
        print(f'  ❌ {f.relative_to(base)}: {e.msg}')

# [2] 핵심 모듈 Import 테스트
print('\n[2] Import 테스트...')
core_modules = [
    'GUI.trading_dashboard',
    'GUI.staru_main',
    'GUI.settings_widget',
    'GUI.backtest_widget',
    'core.unified_bot',
    'core.strategy_core',
    'exchanges.exchange_manager',
]

# Ensure project root is in path
if str(base) not in sys.path:
    sys.path.insert(0, str(base))

for mod in core_modules:
    try:
        __import__(mod)
        print(f'  ✅ {mod}')
    except Exception as e:
        errors.append(f'❌ Import: {mod} - {e}')
        print(f'  ❌ {mod}: {e}')

# [3] reconfigure 관련 검색
print('\n[3] reconfigure 호출 위치...')
for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or '.venv' in str(f) or 'build' in str(f) or 'dist' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        if 'reconfigure' in code:
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if 'reconfigure' in line:
                    print(f'  {f.relative_to(base)} L{i+1}: {line.strip()[:60]}')
    except Exception:

        pass

# [4] 요약
print(f'\n=== 총 {len(errors)}개 에러 ===')
for e in errors:
    print(e)
