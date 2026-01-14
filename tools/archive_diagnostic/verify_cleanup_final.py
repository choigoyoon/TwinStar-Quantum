from pathlib import Path
import re
import sys

# Windows 한글 출력 대응
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

print("=" * 70)
print("core/ + exchanges/ 수정 후 검증")
print("=" * 70)

errors = []
warnings = []

# 1. 문법 검사
print("\n[1] 문법 검사")
folders = ['core', 'exchanges']
for folder in folders:
    folder_path = base / folder
    if folder_path.exists():
        for f in folder_path.glob('*.py'):
            try:
                code = f.read_text(encoding='utf-8', errors='ignore')
                compile(code, f.name, 'exec')
                print(f"  ✅ {folder}/{f.name}")
            except SyntaxError as e:
                print(f"  ❌ {folder}/{f.name}: L{e.lineno}")
                errors.append(f"{folder}/{f.name}")

# 2. except Exception:
     pass 잔여
print("\n[2] except Exception:
     pass 잔여 확인")
for folder in folders:
    folder_path = base / folder
    if folder_path.exists():
        for f in folder_path.glob('*.py'):
            code = f.read_text(encoding='utf-8', errors='ignore')
            matches = re.findall(r'except.*:\s*pass\s*$', code, re.MULTILINE)
            if matches:
                warnings.append(f"{folder}/{f.name}: {len(matches)}개")

if warnings:
    for w in warnings:
        print(f"  ⚠️ {w}")
else:
    print("  ✅ 모두 제거됨")

# 3. 위험한 직접 접근 잔여
print("\n[3] 위험한 API 접근 잔여")
risky = []
for folder in folders:
    folder_path = base / folder
    if folder_path.exists():
        for f in folder_path.glob('*.py'):
            code = f.read_text(encoding='utf-8', errors='ignore')
            lines = code.split('\n')
            for i, line in enumerate(lines):
                # result['key'] or response['key'] but not .get('
                if re.search(r'(result|response)\[["\']', line) and '.get(' not in line:
                    # check if inside try block (heuristic)
                    surrounding = '\n'.join(lines[max(0,i-3):i+1])
                    if 'try' not in surrounding:
                        risky.append(f"{folder}/{f.name} L{i+1}")

if risky:
    print(f"  ⚠️ {len(risky)}개 남음")
    for r in risky[:5]:
        print(f"    {r}")
else:
    print("  ✅ 모두 안전화됨")

# 결과
print("\n" + "=" * 70)
if errors:
    print(f"🔴 문법 에러: {errors}")
elif warnings or risky:
    print(f"🟡 경고 있음 - 추가 수정 필요")
else:
    print("🟢 core/ + exchanges/ 정리 완료!")
    print("→ GUI/ 진행 또는 v1.4.4 최종 배포")
