"""SPEC 파일 vs 실제 프로젝트 비교 검증 (필수 모듈만)"""
from pathlib import Path
import re

base = Path(__file__).parent
spec_file = base / 'staru_clean.spec'

print("=" * 60)
print("SPEC 파일 완전성 검증")
print("=" * 60)

# SPEC 파일에서 hiddenimports 추출
spec_code = spec_file.read_text(encoding='utf-8')
hidden_match = re.search(r'hiddenimports\s*=\s*\[(.*?)\]', spec_code, re.DOTALL)
if hidden_match:
    hidden_text = hidden_match.group(1)
    spec_modules = set(re.findall(r"'([^']+)'", hidden_text))
else:
    spec_modules = set()

print(f"SPEC에 등록된 모듈: {len(spec_modules)}개")

# 실제 프로젝트 필수 모듈만 스캔
actual_modules = set()
folders = ['GUI', 'core', 'exchanges', 'storage', 'utils', 'strategies']

for folder in folders:
    folder_path = base / folder
    if folder_path.exists():
        for py_file in folder_path.glob('*.py'):
            module_name = f"{folder}.{py_file.stem}"
            if py_file.name == '__init__.py':
                module_name = folder
            actual_modules.add(module_name)

print(f"필수 폴더 모듈: {len(actual_modules)}개")

# 누락 모듈 찾기
missing = []
for mod in actual_modules:
    if mod not in spec_modules:
        found = any(mod in sm for sm in spec_modules)
        if not found:
            missing.append(mod)

print(f"\nSPEC에 누락된 필수 모듈: {len(missing)}개")
for m in sorted(missing):
    print(f"  '{m}',")

# datas 검증
print("\n" + "=" * 60)
print("datas 리소스 검증")
print("=" * 60)

datas_match = re.search(r'datas\s*=\s*\[(.*?)\]', spec_code, re.DOTALL)
if datas_match:
    datas_text = datas_match.group(1)
    datas_paths = re.findall(r"\('([^']+)'", datas_text)
    
    missing_files = []
    for dp in datas_paths:
        full_path = base / dp
        if not full_path.exists():
            missing_files.append(dp)
    
    if missing_files:
        print(f"누락된 리소스 {len(missing_files)}개:")
        for f in missing_files:
            print(f"  - {f}")
    else:
        print(f"OK 모든 리소스 파일 존재 ({len(datas_paths)}개)")

print("\n" + "=" * 60)
print("요약")
print("=" * 60)
print(f"  SPEC 모듈: {len(spec_modules)}개")
print(f"  필수 모듈: {len(actual_modules)}개")
print(f"  누락: {len(missing)}개")
