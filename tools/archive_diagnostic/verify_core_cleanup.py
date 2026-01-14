from pathlib import Path
import re
import sys

# Windows 한글 출력 대응
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

print("=" * 70)
print("core/ 수정 후 검증")
print("=" * 70)

errors = []

# 1. 문법 검사
print("\n[1] 문법 검사")
for f in (base / 'core').glob('*.py'):
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        compile(code, f.name, 'exec')
        print(f"  ✅ {f.name}")
    except SyntaxError as e:
        print(f"  ❌ {f.name}: L{e.lineno} {e.msg}")
        errors.append(f.name)

# 2. except Exception:
     pass 잔여 확인
print("\n[2] except Exception:
     pass 잔여 확인")
remaining = 0
for f in (base / 'core').glob('*.py'):
    code = f.read_text(encoding='utf-8', errors='ignore')
    # except...: pass (공백/탭 포함)
    matches = re.findall(r'except.*:\s*pass', code)
    if matches:
        remaining += len(matches)
        print(f"  ⚠️ {f.name}: {len(matches)}개 남음")
        for m in matches:
            print(f"    - {m}")

if remaining == 0:
    print("  ✅ 모두 제거됨")

# 3. 결과
print("\n" + "=" * 70)
if errors:
    print(f"❌ 문법 에러: {errors}")
else:
    print("✅ core/ 정리 완료")
