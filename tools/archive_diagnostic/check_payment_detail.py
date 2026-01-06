from pathlib import Path
import re

base = Path(r'C:\매매전략')

# 1) unified_bot.py에서 tier 관련 로직 확인
print('=== unified_bot.py tier 로직 ===')
bot = base / 'core' / 'unified_bot.py'
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    for i, line in enumerate(lines):
        if 'tier' in line.lower() and ('=' in line or 'if' in line):
            print(f'L{i+1}: {line.strip()[:100]}')
else:
    print('❌ unified_bot.py 없음')

# 2) payment_dialog.py 전체 구조
print('\n=== payment_dialog.py 함수 목록 ===')
found_payment = False
for f in base.rglob('payment_dialog.py'):
    if '__pycache__' not in str(f):
        found_payment = True
        code = f.read_text(encoding='utf-8', errors='ignore')
        funcs = re.findall(r'def (\w+)\(', code)
        print(f'파일: {f}')
        print(f'함수: {funcs}')
        print(f'줄 수: {len(code.split(chr(10)))}')

if not found_payment:
    print('❌ payment_dialog.py 없음')
