import os

# 1. 실제 존재하는 모든 py 파일
all_py = []
for root, dirs, files in os.walk('.'):
    if 'dist' in root or 'build' in root or '__pycache__' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            rel = os.path.relpath(os.path.join(root, f), '.')
            all_py.append(rel)

print(f'=== 전체 .py 파일: {len(all_py)}개 ===')

# 2. spec 파일 읽기
with open('staru_clean.spec', 'r', encoding='utf-8') as f:
    spec_content = f.read()

# 3. 누락 체크
print('\n=== 누락 가능성 체크 ===')
dirs_to_check = ['core', 'exchanges', 'utils', 'GUI', 'strategies']
missing = []
for d in dirs_to_check:
    if os.path.exists(d):
        for f in os.listdir(d):
            if f.endswith('.py') and not f.startswith('__'):
                module = f'{d}.{f[:-3]}'
                if module not in spec_content:
                    missing.append(module)
                    print(f'❌ 누락: {module}')

if not missing:
    print('✅ 모든 모듈이 spec에 포함됨')
else:
    print(f'\n총 {len(missing)}개 누락')

# 4. 버전 확인
print('\n=== 버전 확인 ===')
if os.path.exists('version.txt'):
    with open('version.txt', 'r') as f:
        version = f.read().strip()
    print(f'version.txt: {version}')
