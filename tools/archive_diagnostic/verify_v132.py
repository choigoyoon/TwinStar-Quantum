from pathlib import Path
import re
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

print("=" * 60)
print("v1.3.2 배포 전 검증")
print("=" * 60)

errors = []

# 1. 문법 검사
print("\n[1] 문법 검사")
for f in ['exchanges/binance_exchange.py', 'exchanges/bybit_exchange.py', 
          'exchanges/bitget_exchange.py', 'exchanges/okx_exchange.py',
          'exchanges/bingx_exchange.py', 'core/unified_bot.py']:
    path = base / f
    if path.exists():
        try:
            code = path.read_text(encoding='utf-8', errors='ignore')
            compile(code, f, 'exec')
            print(f"  ✅ {f}")
        except SyntaxError as e:
            print(f"  ❌ {f}: L{e.lineno} {e.msg}")
            errors.append(f)

# 2. 레버리지 에러 처리 확인
print("\n[2] 레버리지 에러 처리")
checks = {
    'binance_exchange.py': ['-4028', 'No need'],
    'bybit_exchange.py': ['110043'],
    'bitget_exchange.py': ['not modified', 'already'],
    'okx_exchange.py': ['not modified', 'already'],
    'bingx_exchange.py': ['not modified', 'already'],
}

for f, keywords in checks.items():
    path = base / 'exchanges' / f
    if path.exists():
        code = path.read_text(encoding='utf-8', errors='ignore')
        found = any(kw.lower() in code.lower() for kw in keywords)
        status = '✅' if found else '❌'
        print(f"  {status} {f}")
        if not found:
            errors.append(f)

# 3. version.json
print("\n[3] version.json")
ver_file = base / 'version.json'
ver = json.loads(ver_file.read_text(encoding='utf-8'))
print(f"  현재: {ver.get('version')}")

# 결과
print("\n" + "=" * 60)
if errors:
    print(f"❌ {len(errors)}개 문제 - 수정 후 배포")
else:
    print("✅ 검증 통과 - v1.3.2 배포 가능")
    print("\n버전 1.3.2로 올리고 빌드 진행해")
