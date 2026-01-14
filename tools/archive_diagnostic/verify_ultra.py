# verify_ultra.py - 극한 검증
import os
import re
from pathlib import Path

base = Path(__file__).parent

print("=" * 60)
print("극한 검증: 숨겨진 모든 문제 탐색")
print("=" * 60)

issues = []

# 1. async 내 time.sleep
print("\n[1] 비동기/동기 혼용")
for py in base.rglob("*.py"):
    if '__pycache__' in str(py): continue
    try:
        code = py.read_text(encoding='utf-8', errors='ignore')
        if 'async def' in code and 'time.sleep(' in code:
            print(f"  ! {py.name}: time.sleep in async")
            issues.append(f"! {py.name}: async+time.sleep")
    except Exception:

        pass

# 2. except Exception:
     pass
print("\n[2] 예외 삼킴 (except + pass)")
count = 0
for py in base.rglob("*.py"):
    if '__pycache__' in str(py): continue
    try:
        code = py.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if re.match(r'\s*except.*:\s*$', line):
                if i+1 < len(lines) and lines[i+1].strip() == 'pass':
                    count += 1
    except Exception:

        pass
print(f"  발견: {count}개")

# 3. 스레드 안전성
print("\n[3] 스레드 안전성")
bot = base / 'core' / 'unified_bot.py'
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    has_thread = 'threading' in code
    has_lock = 'Lock' in code
    if has_thread and has_lock:
        print("  OK 스레드 + Lock 사용")
    elif has_thread:
        print("  ! 스레드 but Lock 없음")
        issues.append("! 스레드 Lock 없음")
    else:
        print("  OK 스레드 미사용")

# 4. 파일 핸들
print("\n[4] 파일 핸들")
for py in [base/'core'/'unified_bot.py', base/'core'/'strategy_core.py']:
    if py.exists():
        code = py.read_text(encoding='utf-8', errors='ignore')
        opens = len(re.findall(r'open\(', code))
        withs = len(re.findall(r'with open\(', code))
        if opens > withs:
            print(f"  ! {py.name}: open {opens}, with {withs}")
        else:
            print(f"  OK {py.name}: with 사용")

# 5. 순환 참조
print("\n[5] 순환 참조 검사")
imports_map = {}
for py in base.rglob("*.py"):
    if '__pycache__' in str(py): continue
    try:
        code = py.read_text(encoding='utf-8', errors='ignore')
        froms = re.findall(r'from\s+(\w+)\s+import', code)
        imports_map[py.stem] = set(froms)
    except Exception:

        pass

cycles = 0
for mod, deps in imports_map.items():
    for dep in deps:
        if dep in imports_map and mod in imports_map.get(dep, []):
            cycles += 1
            print(f"  ! {mod} <-> {dep}")
print(f"  순환 가능: {cycles}개")

# 6. API 응답 검증
print("\n[6] 주문 후 응답 체크")
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    order_lines = []
    for i, line in enumerate(lines):
        if 'place_market_order' in line and 'def ' not in line:
            next5 = '\n'.join(lines[i:i+5])
            if 'result' in next5 or 'if ' in next5 or 'order' in next5:
                print(f"  OK L{i+1}: 응답 체크 있음")
            else:
                order_lines.append(i+1)
    if order_lines:
        print(f"  ! L{order_lines}: 응답 체크 권장")

# 결과
print("\n" + "=" * 60)
crit = len([i for i in issues if 'X' in i])
warn = len([i for i in issues if '!' in i])
print(f"치명적: {crit}개, 경고: {warn}개")
for i in issues:
    print(f"  {i}")
if crit == 0:
    print("\nOK 치명적 문제 없음 - 빌드 가능")
else:
    print("\nX 수정 필요")
print("=" * 60)
