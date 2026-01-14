# verify_logic.py - 논리적 문제 + 중복 + 백업 검증
import os
import re
from collections import defaultdict

base_path = rstr(Path(__file__).parent)

print("=" * 60)
print("논리적 문제 + 중복 + 백업 검증")
print("=" * 60)

issues = []

# 파일 로드
bot_path = os.path.join(base_path, 'core/unified_bot.py')
with open(bot_path, 'r', encoding='utf-8') as f:
    bot_content = f.read()
    bot_lines = bot_content.split('\n')

# [1] 논리적 문제
print("\n[1] 논리적 문제")

# 1-1. 포지션 체크
if 'if self.position' in bot_content or 'if not self.position' in bot_content:
    print("  OK 포지션 체크 존재")
else:
    issues.append("X 포지션 체크 없음")
    print("  X 포지션 체크 없음")

# 1-2. 무한루프
if 'while True' in bot_content and 'break' in bot_content:
    print("  OK while True에 break 존재")
elif 'while True' not in bot_content:
    print("  OK while True 없음")
else:
    issues.append("X 무한루프 위험")

# 1-3. 스레드 안전
if 'Lock' in bot_content or 'lock' in bot_content:
    print("  OK Lock 사용")
else:
    print("  ! Lock 없음 (스레드 미사용 시 OK)")

# [2] 중복 코드
print("\n[2] 중복 코드")

# 파일 내 중복 함수
for filepath in [bot_path, os.path.join(base_path, 'core/strategy_core.py')]:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    funcs = re.findall(r'^def (\w+)\(', content, re.MULTILINE)
    dups = [x for x in set(funcs) if funcs.count(x) > 1]
    name = os.path.basename(filepath)
    if dups:
        issues.append(f"X 중복함수: {name} {dups}")
        print(f"  X {name}: {dups}")
    else:
        print(f"  OK {name}: 중복 없음")

# [3] 상태 관리
print("\n[3] 상태 관리")
pos_sets = len(re.findall(r'self\.position\s*=', bot_content))
pos_clears = len(re.findall(r'self\.position\s*=\s*None', bot_content))
saves = len(re.findall(r'save_state\(\)', bot_content))

print(f"  포지션 설정: {pos_sets}회")
print(f"  포지션 초기화: {pos_clears}회")
print(f"  save_state: {saves}회")

if pos_sets > 0 and pos_clears > 0:
    print("  OK 포지션 관리 정상")

# [4] 백업 파일
print("\n[4] 백업 파일")
backup_count = 0
for root, dirs, files in os.walk(base_path):
    if any(x in root for x in ['__pycache__', '.git', 'dist']):
        continue
    for f in files:
        if '.bak' in f or '_backup' in f:
            backup_count += 1
print(f"  발견된 백업: {backup_count}개")

# [5] 데이터 무결성
print("\n[5] 데이터 무결성")
if 'df_entry_full.empty' in bot_content or 'len(df' in bot_content:
    print("  OK DataFrame empty/len 체크")
else:
    print("  ! DataFrame 체크 확인 필요")

iloc_count = bot_content.count('iloc[')
len_count = bot_content.count('len(')
print(f"  iloc: {iloc_count}회, len: {len_count}회")

# 결과
print("\n" + "=" * 60)
print(f"문제: {len(issues)}개")
for i in issues:
    print(f"  {i}")

if len(issues) == 0:
    print("\nOK 논리적 문제 없음 - 빌드 가능")
else:
    print("\nX 문제 있음 - 확인 필요")
print("=" * 60)
