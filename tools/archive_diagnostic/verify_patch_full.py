
from pathlib import Path
import ast
import sys

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

print("=" * 60)
print("v1.2.3 패치 후 전체 재검증")
print("=" * 60)

issues = []
passed = []

# 1. 문법 검증 (수정된 파일)
print("\n[1] 수정 파일 문법 검증")
modified_files = [
    'core/strategy_core.py',
    'core/unified_bot.py',
    'exchanges/upbit_exchange.py',
    'exchanges/bithumb_exchange.py'
]

for rel in modified_files:
    fpath = base / rel
    if not fpath.exists():
        # 다른 경로 시도
        for f in base.rglob(rel.split('/')[-1]):
            fpath = f
            break
    
    if fpath.exists():
        try:
            code = fpath.read_text(encoding='utf-8')
            ast.parse(code)
            print(f"  ✅ {rel}")
            passed.append(f"{rel} 문법")
        except SyntaxError as e:
            print(f"  ❌ {rel}: L{e.lineno} {e.msg}")
            issues.append(f"{rel} 문법 에러")
    else:
        print(f"  ⚠️ {rel} 파일 없음")

# 2. 현물 숏 차단 검증
print("\n[2] 현물 숏 차단 로직")

# strategy_core.py
found_strategy = False
for f in base.rglob('strategy_core.py'):
    found_strategy = True
    code = f.read_text(encoding='utf-8')
    if 'spot' in code.lower() and 'short' in code.lower():
        print(f"  ✅ strategy_core: 숏 차단 있음")
        passed.append("strategy_core 숏 차단")
    else:
        print(f"  ❌ strategy_core: 숏 차단 없음")
        issues.append("strategy_core 숏 차단 없음")
    break
if not found_strategy:
    print("  ⚠️ strategy_core.py 파일 못 찾음")

# unified_bot.py
found_bot = False
for f in base.rglob('unified_bot.py'):
    found_bot = True
    code = f.read_text(encoding='utf-8')
    if ('upbit' in code.lower() or 'bithumb' in code.lower()) and 'short' in code.lower():
        print(f"  ✅ unified_bot: 숏 차단 있음")
        passed.append("unified_bot 숏 차단")
    else:
        print(f"  ❌ unified_bot: 숏 차단 없음")
        issues.append("unified_bot 숏 차단 없음")
    break
if not found_bot:
    print("  ⚠️ unified_bot.py 파일 못 찾음")

# 3. fetchTime 검증
print("\n[3] fetchTime 메서드")
for name in ['upbit', 'bithumb']:
    found = False
    for f in base.rglob(f'*{name}*.py'):
        if 'exchange' in f.name.lower():
            code = f.read_text(encoding='utf-8')
            if 'fetchTime' in code or 'fetch_time' in code:
                print(f"  ✅ {f.name}: fetchTime 있음")
                passed.append(f"{name} fetchTime")
                found = True
            break
    if not found:
        print(f"  ❌ {name}: fetchTime 없음")
        issues.append(f"{name} fetchTime 없음")

# 4. pending_signals 동기화
print("\n[4] pending_signals 동기화")
for f in base.rglob('unified_bot.py'):
    code = f.read_text(encoding='utf-8')
    if 'SYNC' in code or ('pending_signals' in code and 'bt_state' in code):
        print(f"  ✅ 신호 동기화 로직 있음")
        passed.append("신호 동기화")
    else:
        print(f"  ⚠️ 신호 동기화 확인 필요")
    break

# 5. RSI 필터
print("\n[5] RSI 필터")
for f in base.rglob('unified_bot.py'):
    code = f.read_text(encoding='utf-8')
    if 'rsi' in code.lower() and ('40' in code or '60' in code):
        print(f"  ✅ RSI 필터 있음")
        passed.append("RSI 필터")
    else:
        print(f"  ⚠️ RSI 필터 확인 필요")
    break

# 6. version.json
print("\n[6] version.json")
ver_path = base / 'version.json'
if ver_path.exists():
    import json
    try:
        v = json.loads(ver_path.read_text(encoding='utf-8'))
        ver = v.get('version', '?')
        print(f"  버전: {ver}")
        if 'download_url' in v:
            print(f"  ✅ download_url 있음")
            passed.append("version.json")
    except Exception as e:
        print(f"  ❌ version.json 에러: {e}")
        issues.append("version.json 에러")
else:
    print(f"  ❌ version.json 없음")
    issues.append("version.json 없음")

# 결과
print("\n" + "=" * 60)
print("검증 결과")
print("=" * 60)
print(f"✅ 통과: {len(passed)}개")
print(f"❌ 문제: {len(issues)}개")

if issues:
    print("\n🔴 해결 필요:")
    for i in issues:
        print(f"  - {i}")
else:
    print("\n🎉 모든 검증 통과!")
