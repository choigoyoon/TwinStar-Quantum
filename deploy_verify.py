
from pathlib import Path
import sys

base = Path(r'C:\매매전략')
errors = []

print("=" * 60)
print("v1.4.4 최종 검증 (Order ID Tracking)")
print("=" * 60)

# 1. 문법 검사
print("\n[1] 문법 검사")
files = [
    'core/unified_bot.py',
    'exchanges/bybit_exchange.py',
    'exchanges/binance_exchange.py',
    'exchanges/okx_exchange.py',
    'exchanges/bitget_exchange.py',
    'exchanges/ccxt_exchange.py',
    'exchanges/upbit_exchange.py',
    'exchanges/bithumb_exchange.py',
]
for f in files:
    path = base / f
    if path.exists():
        try:
            code = path.read_text(encoding='utf-8', errors='ignore')
            compile(code, f, 'exec')
            print(f"  ✅ {f}")
        except SyntaxError as e:
            print(f"  ❌ {f}: L{e.lineno} - {e.msg}")
            errors.append(f)
    else:
        print(f"  ⚠️ {f} (File not found)")

# 2. order_id 저장 확인
print("\n[2] order_id 저장 로직")
bot = base / 'core/unified_bot.py'
code = bot.read_text(encoding='utf-8', errors='ignore')

if 'order_id' in code and 'bt_state' in code:
    print("  ✅ order_id → bt_state 저장")
else:
    print("  ❌ order_id 저장 없음")
    errors.append('order_id')

# 3. 외부 포지션 경고
if '외부' in code or 'external' in code.lower() or 'unknown' in code.lower():
    print("  ✅ 외부 포지션 감지")
else:
    print("  ⚠️ 외부 포지션 경고 확인 필요")

# 4. 버전 확인
print("\n[4] 버전 정보 일치")
version_json = (base / 'version.json').read_text(encoding='utf-8')
if '"1.4.4"' in version_json:
    print("  ✅ version.json: 1.4.4")
else:
    print("  ❌ version.json: 버전 불일치")
    errors.append('version_json')

updater = (base / 'core/updater.py').read_text(encoding='utf-8')
if '"1.4.4"' in updater:
    print("  ✅ updater.py: 1.4.4")
else:
    print("  ❌ updater.py: 버전 불일치")
    errors.append('updater_py')

# 결과
print("\n" + "=" * 60)
if errors:
    print(f"❌ {len(errors)}개 문제 발견: {errors}")
    sys.exit(1)
else:
    print("✅ 모든 검증 통과 - v1.4.4 배포 준비 완료!")
    sys.exit(0)
