"""
중복 분석 스크립트
"""
import os
import re
from collections import defaultdict
from pathlib import Path

BASE = str(Path(__file__).parent)
os.chdir(BASE)

print('=' * 60)
print('=== 중복 분석 결과 ===')
print('=' * 60)
print()

# 1. 동일 파일명 확인
print('[1] 동일 파일명')
print('-' * 40)
names = defaultdict(list)
for root, dirs, files in os.walk('.'):
    if '__pycache__' in root or '.git' in root or 'tools' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            names[f].append(os.path.join(root, f))

dup_files = [(name, paths) for name, paths in names.items() if len(paths) > 1]
if dup_files:
    for name, paths in dup_files:
        print(f'{name}:')
        for p in paths:
            print(f'  - {p}')
else:
    print('✅ 중복 파일명 없음')
print()

# 2. 중복 클래스명 확인
print('[2] 중복 클래스명')
print('-' * 40)
classes = defaultdict(list)
for root, dirs, files in os.walk('.'):
    if '__pycache__' in root or '.git' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            try:
                with open(path, 'r', encoding='utf-8') as file:
                    for i, line in enumerate(file, 1):
                        match = re.match(r'^class\s+(\w+)', line)
                        if match:
                            classes[match.group(1)].append(f'{path}:{i}')
            except Exception:

                pass

# Filter: only actual duplicates (exclude Paths fallback etc)
dup_classes = [(name, locs) for name, locs in classes.items() 
               if len(locs) > 1 and name not in ['Paths', 'DummyGuard', 'Position']]
if dup_classes:
    for name, locs in sorted(dup_classes):
        print(f'{name}:')
        for loc in locs:
            print(f'  - {loc}')
else:
    print('✅ 중복 클래스명 없음 (의도적 폴백 제외)')
print()

# 3. GUI 구조 확인
print('[3] GUI 하위 폴더 구조')
print('-' * 40)
for folder in ['GUI/components', 'GUI/dashboard']:
    full_path = os.path.join(BASE, folder)
    if os.path.exists(full_path):
        files = [f for f in os.listdir(full_path) if f.endswith('.py')]
        print(f'{folder}/: ({len(files)} files)')
        for f in sorted(files):
            print(f'  - {f}')
    else:
        print(f'{folder}/: 없음')
print()

# 4. 결론
print('=' * 60)
print('=== 결론 ===')
print('=' * 60)

if dup_files or dup_classes:
    print('⚠️ 중복 발견 - 확인 필요')
    if dup_files:
        print(f'  - 파일명 중복: {len(dup_files)}개')
    if dup_classes:
        print(f'  - 클래스명 중복: {len(dup_classes)}개')
else:
    print('✅ 중복 없음 - Phase 10.3 진행 가능')
