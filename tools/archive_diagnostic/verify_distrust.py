from pathlib import Path
import re
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

print("=" * 60)
print("실제 수정 확인 (불신 검증)")
print("=" * 60)

# 1. BingX 문법 검사
print("\n[1] BingX 문법")
bingx = base / 'exchanges/bingx_exchange.py'
if bingx.exists():
    code = bingx.read_text(encoding='utf-8', errors='ignore')
    try:
        compile(code, 'bingx', 'exec')
        print("  ✅ 문법 정상")
    except SyntaxError as e:
        print(f"  ❌ 문법 에러: L{e.lineno} {e.msg}")

# 2. get_kline 호출 순서
print("\n[2] get_kline 조기 호출")
bot = base / 'core/unified_bot.py'
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

# __init__ 내에서 get_kline 호출 찾기
in_init = False
found_kline_in_init = False
for i, line in enumerate(lines):
    if 'def __init__' in line:
        in_init = True
    if in_init and line.strip().startswith('def ') and '__init__' not in line:
        in_init = False
    if in_init and 'get_kline' in line and '#' not in line.split('get_kline')[0]:
        print(f"  ⚠️ __init__ 내 get_kline: L{i+1}")
        print(f"     {line.strip()[:50]}")
        found_kline_in_init = True

if not found_kline_in_init:
    print("  ✅ __init__ 내 get_kline 없음 (안전)")

# 3. Session 생성 위치
print("\n[3] Session 생성 위치")
for i, line in enumerate(lines):
    if 'self.session' in line and '=' in line and 'None' not in line:
        print(f"  L{i+1}: {line.strip()[:50]}")
        break

# 4. 실제 봇 시작해서 에러 확인
print("\n[4] 빠른 Import 테스트")
sys.path.insert(0, str(base))
try:
    from core.unified_bot import UnifiedBot
    print("  ✅ UnifiedBot import 성공")
except Exception as e:
    print(f"  ❌ Import 실패: {e}")

print("\n" + "=" * 60)
print("결론: 봇 재시작해서 Kline 에러 안 뜨면 진짜 수정된 거")
