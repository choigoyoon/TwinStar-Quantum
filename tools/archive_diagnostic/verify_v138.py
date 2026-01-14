from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent
bot = base / 'core/unified_bot.py'
code = bot.read_text(encoding='utf-8', errors='ignore')

print('v1.3.8 수정 사항 확인:')
print('=' * 60)

errors = []

# 1. 중복 진입 방지
if 'Already in position' in code:
    print('OK 중복 진입 방지 (bt_state 체크)')
else:
    print('ERR 중복 진입 방지 없음')
    errors.append('dup check')

if 'Exchange has open position' in code:
    print('OK 중복 진입 방지 (거래소 체크)')
else:
    print('ERR 거래소 포지션 체크 없음')
    errors.append('ex check')

# 2. bt_state 저장
if "bt_state" in code and "'position':" in code:
    print('OK bt_state 저장')
else:
    print('WARN bt_state 저장 확인 필요')

# 3. 문법 검사
try:
    compile(code, 'unified_bot.py', 'exec')
    print('OK 문법 검사 통과')
except SyntaxError as e:
    print(f'ERR 문법 에러: L{e.lineno}')
    errors.append('syntax')

print()
if not errors:
    print('PASS v1.3.8 배포 가능')
else:
    print(f'FAIL {len(errors)}개 문제: {errors}')
