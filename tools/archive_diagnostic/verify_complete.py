# verify_complete.py - 전체 시스템 완전 검증
import os
import re
import json

base_path = rstr(Path(__file__).parent)

print("=" * 60)
print("전체 시스템 완전 검증")
print("=" * 60)

all_issues = []

# 1. updater.py 분석
print("\n[1] 업데이트 시스템")
updater_path = os.path.join(base_path, 'core/updater.py')
if os.path.exists(updater_path):
    with open(updater_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    ver_match = re.search(r'CURRENT_VERSION\s*=\s*["\']([^"\']+)["\']', content)
    if ver_match:
        print(f"  CURRENT_VERSION: {ver_match.group(1)}")
    
    url_match = re.search(r'VERSION_URL\s*=\s*["\']([^"\']+)["\']', content)
    if url_match:
        print(f"  VERSION_URL: {url_match.group(1)}")
    
    if 'timeout' in content:
        print("  OK: timeout 설정 있음")
    else:
        all_issues.append("WARN updater.py: timeout 없음")

# 2. version.json
print("\n[2] version.json 분석")
vj_path = os.path.join(base_path, 'version.json')
if os.path.exists(vj_path):
    with open(vj_path, 'rb') as f:
        raw = f.read(3)
    if raw == b'\xef\xbb\xbf':
        all_issues.append("ERR version.json: BOM 있음")
        print("  X BOM 있음")
    else:
        print("  OK BOM 없음")
    
    with open(vj_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    print(f"  latest_version: {data.get('latest_version')}")
    
    if 'download_url' not in data:
        all_issues.append("ERR version.json: download_url 없음")
        print("  X download_url 없음")
    else:
        print(f"  OK download_url: {data.get('download_url')}")
    
    if 'patch_url' in data:
        all_issues.append("WARN version.json: patch_url 잔재")
        print("  ! patch_url 잔재 (ZIP)")

# 3. 라이센스 파일
print("\n[3] 라이센스 시스템")
for lf in ['license_manager.py', 'core/license_guard.py', 'license_tiers.py']:
    path = os.path.join(base_path, lf)
    if os.path.exists(path):
        print(f"  OK {lf}")
    else:
        all_issues.append(f"ERR {lf}: 없음")
        print(f"  X {lf} 없음")

# 4. 하드코딩 경로
print("\n[4] 하드코딩 경로 검색")
found_paths = 0
for root, dirs, files in os.walk(base_path):
    if any(x in root for x in ['__pycache__', '.git', 'dist', 'build', 'venv', '_backup']):
        continue
    for f in files:
        if f.endswith('.py'):
            try:
                with open(os.path.join(root, f), 'r', encoding='utf-8') as file:
                    content = file.read()
                if 'C:\\\\twinstar' in content or 'C:/twinstar' in content:
                    if found_paths < 5:
                        all_issues.append(f"WARN 하드코딩: {f}")
                    found_paths += 1
            except Exception:

                pass
print(f"  발견: {found_paths}개")

# 결과
print("\n" + "=" * 60)
print(f"발견된 문제: 총 {len(all_issues)}개")
print("=" * 60)

errs = [i for i in all_issues if i.startswith('ERR')]
warns = [i for i in all_issues if i.startswith('WARN')]

print(f"\nERR (심각): {len(errs)}개")
for e in errs:
    print(f"  {e}")

print(f"\nWARN (경고): {len(warns)}개")
for w in warns[:10]:
    print(f"  {w}")

print("\n완료")
