from pathlib import Path
import json
import re

base = Path(r'C:\매매전략')

print('=' * 70)
print('🔒 빌드 시 민감 정보 유출 점검')
print('=' * 70)

issues = []

#############################################
# [1] spec 파일에서 포함되는 데이터 확인
#############################################
print('\n📌 [1] spec 파일 분석')

spec_file = base / 'staru_clean.spec'
if spec_file.exists():
    code = spec_file.read_text(encoding='utf-8', errors='ignore')
    
    # datas 항목 찾기
    print('\n  [포함되는 데이터 (datas)]:')
    datas_match = re.search(r'datas\s*=\s*\[(.*?)\]', code, re.DOTALL)
    if datas_match:
        datas = datas_match.group(1)
        print(f'    {datas[:200]}...')
        
        # 위험 패턴
        dangerous = ['config', 'key', 'secret', 'api', 'credential', 'token'] # removed .json to avoid too many false positives if needed, but original had it
        for d in dangerous:
            if d.lower() in datas.lower():
                issues.append(f'spec datas에 {d} 포함 가능성')
                print(f'    ⚠️ {d} 발견!')

#############################################
# [2] JSON 설정 파일 내 API 키 확인
#############################################
print('\n📌 [2] JSON 파일 내 민감 정보')

sensitive_keys = ['api_key', 'secret', 'password', 'token', 'key', 'credential', 'api-key', 'secret-key']

for f in base.rglob('*.json'):
    if '__pycache__' in str(f) or '.venv' in str(f) or 'node_modules' in str(f):
        continue
    try:
        data = json.loads(f.read_text(encoding='utf-8'))
        fname = f.relative_to(base).as_posix()
        
        def check_dict(d, path=''):
            found = []
            if isinstance(d, dict):
                for k, v in d.items():
                    full_path = f'{path}.{k}' if path else k
                    if any(s in k.lower() for s in sensitive_keys):
                        # Filter out common non-sensitive keys that might match
                        non_sensitive = ['key_type', 'keyboard', 'key_range']
                        if not any(ns in k.lower() for ns in non_sensitive):
                            if v and str(v) != '' and str(v) != 'None' and len(str(v)) > 5:
                                found.append((full_path, str(v)[:20]))
                    if isinstance(v, dict):
                        found.extend(check_dict(v, full_path))
            elif isinstance(d, list):
                for i, item in enumerate(d):
                    found.extend(check_dict(item, f'{path}[{i}]'))
            return found
        
        sensitive = check_dict(data)
        if sensitive:
            print(f'\n  ⚠️ {fname}:')
            for path, val in sensitive:
                print(f'    {path}: {val}...')
                issues.append(f'{fname} 내 {path}')
    except:
        pass

#############################################
# [3] Python 코드 내 하드코딩된 키
#############################################
print('\n📌 [3] 코드 내 하드코딩된 키')

api_patterns = [
    r'(?<!_)api_key\s*=\s*["\'][^"\']{15,}["\']',
    r'(?<!_)secret\s*=\s*["\'][^"\']{15,}["\']',
    r'(?<!_)password\s*=\s*["\'][^"\']{8,}["\']',
]

for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or '.venv' in str(f) or 'node_modules' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        fname = f.relative_to(base).as_posix()
        
        for pattern in api_patterns:
            matches = re.findall(pattern, code, re.I)
            if matches:
                # Exclude common test or example code patterns
                clean_matches = [m for m in matches if 'example' not in m.lower() and 'your_' not in m.lower()]
                if clean_matches:
                    print(f'  ⚠️ {fname}: {clean_matches[0][:50]}...')
                    issues.append(f'{fname} 하드코딩 키')
    except:
        pass

#############################################
# [4] 빌드 제외 권장 파일/폴더
#############################################
print('\n📌 [4] 빌드 제외 권장 목록')

exclude_recommend = [
    'config/api_keys.json',
    'config/credentials.json',
    'data/cache/*.parquet',
    '*.log',
    '__pycache__',
    '.env',
    'secrets/',
]

print('  빌드 시 제외해야 할 항목:')
for item in exclude_recommend:
    print(f'    - {item}')

#############################################
# [5] 요약
#############################################
print('\n' + '=' * 70)
print('📋 요약')
print('=' * 70)

if issues:
    print(f'\n🔴 발견된 문제: {len(issues)}개')
    # Filter unique file-based issues for summary to avoid overwhelming output
    unique_files = sorted(list(set([i.split(' ')[0] for i in issues])))
    for f in unique_files:
        print(f'  - {f}')
    print('\n⚠️ 빌드 전 위 파일들의 민감 정보 제거 필요!')
else:
    print('\n✅ 민감 정보 유출 위험 없음')
