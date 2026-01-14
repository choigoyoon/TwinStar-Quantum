from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

print("=" * 60)
print("v1.3.3 배포 전 검증")
print("=" * 60)

errors = []

# 1. 문법 검사
print("\n[1] 문법 검사")
files = [
    'exchanges/bybit_exchange.py',
    'exchanges/binance_exchange.py',
    'core/unified_bot.py',
]
for f in files:
    path = base / f
    try:
        code = path.read_text(encoding='utf-8', errors='ignore')
        compile(code, f, 'exec')
        print(f"  ✅ {f}")
    except SyntaxError as e:
        print(f"  ❌ {f}: L{e.lineno} {e.msg}")
        errors.append(f)

# 2. Bybit 110043 처리 확인
print("\n[2] Bybit 110043 처리")
bybit = base / 'exchanges/bybit_exchange.py'
code = bybit.read_text(encoding='utf-8', errors='ignore')

has_retcode = 'ret_code == 110043' in code or 'retCode == 110043' in code
has_retmsg = '110043' in code and 'ret_msg' in code.lower()
has_exception = 'except' in code and '110043' in code

print(f"  retCode 체크: {'✅' if has_retcode else '❌'}")
print(f"  retMsg 체크: {'✅' if has_retmsg else '❌'}")
print(f"  Exception 체크: {'✅' if has_exception else '⚠️'}")

if not (has_retcode or has_retmsg):
    errors.append('bybit 110043')

# 3. unified_bot 레버리지 실패 후 진행 확인
print("\n[3] unified_bot 레버리지 로직")
bot = base / 'core/unified_bot.py'
code2 = bot.read_text(encoding='utf-8', errors='ignore')

# 레버리지 실패해도 진입 시도하는지
if 'Leverage' in code2 and 'failed' in code2.lower():
    # return False 찾기
    lines = code2.split('\n')
    for i, line in enumerate(lines):
        if 'leverage' in line.lower() and 'failed' in line.lower():
            next_lines = lines[i:i+5]
            has_return = any('return' in l for l in next_lines)
            print(f"  L{i+1}: 실패 후 return: {'⚠️ 있음' if has_return else '✅ 없음'}")

# 4. 실제 봇 Import 테스트
print("\n[4] Import 테스트")
sys.path.insert(0, str(base))
try:
    from exchanges.bybit_exchange import BybitExchange
    print("  ✅ BybitExchange import 성공")
except Exception as e:
    print(f"  ❌ Import 실패: {e}")
    errors.append('import')

# 결과
print("\n" + "=" * 60)
if errors:
    print(f"❌ {len(errors)}개 문제: {errors}")
else:
    print("✅ 검증 통과")
    print("\n봇 재시작해서 실제 테스트:")
    print("  - 110043 에러 시 진입 진행되는지 확인")
