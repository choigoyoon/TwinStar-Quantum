"""spec 파일 + 패키지 구성 전체 점검"""
from pathlib import Path
import re
import sys
import os

base = Path(r'C:\매매전략')
spec_file = base / 'staru_clean.spec'

print("=" * 70)
print("🔍 SPEC 파일 및 패키지 구성 점검")
print("=" * 70)

# ============================================================
# [1] SPEC 파일 분석
# ============================================================
print("\n[1] SPEC 파일 분석")
print("-" * 50)

if not spec_file.exists():
    print("❌ staru_clean.spec 없음")
    exit()

spec_content = spec_file.read_text(encoding='utf-8')

# hiddenimports 추출
hidden_match = re.search(r'hiddenimports\s*=\s*\[(.*?)\]', spec_content, re.DOTALL)
if hidden_match:
    hidden_raw = hidden_match.group(1)
    hidden_imports = re.findall(r"'([^']+)'", hidden_raw)
    print(f"  hiddenimports: {len(hidden_imports)}개")
    
    # 카테고리별 분류
    categories = {
        'core': [h for h in hidden_imports if h.startswith('core.')],
        'GUI': [h for h in hidden_imports if h.startswith('GUI.')],
        'exchanges': [h for h in hidden_imports if h.startswith('exchanges.')],
        'utils': [h for h in hidden_imports if h.startswith('utils.')],
        'storage': [h for h in hidden_imports if h.startswith('storage.')],
        'external': [h for h in hidden_imports if '.' not in h or not h.split('.')[0] in ['core','GUI','exchanges','utils','storage']],
    }
    
    for cat, items in categories.items():
        if items:
            print(f"    {cat}: {len(items)}개")
else:
    print("  ❌ hiddenimports 파싱 실패")
    hidden_imports = []

# datas 추출
datas_match = re.search(r'datas\s*=\s*\[(.*?)\]', spec_content, re.DOTALL)
if datas_match:
    datas_raw = datas_match.group(1)
    datas = re.findall(r"\('([^']+)'", datas_raw)
    print(f"  datas: {len(datas)}개")
else:
    print("  datas: 0개")

# ============================================================
# [2] 프로젝트 실제 구조 vs SPEC 비교
# ============================================================
print("\n[2] 프로젝트 구조 vs SPEC 비교")
print("-" * 50)

# 실제 모듈 수집 (하위 디렉토리 포함)
actual_modules = set()
for folder in ['core', 'GUI', 'exchanges', 'utils', 'storage']:
    folder_path = base / folder
    if folder_path.exists():
        for py_file in folder_path.rglob('*.py'):
            if py_file.name != '__init__.py' and '_backup' not in str(py_file):
                # 상대 경로를 모듈 이름으로 변환
                rel_path = py_file.relative_to(base)
                module_name = str(rel_path.with_suffix('')).replace(os.sep, '.')
                actual_modules.add(module_name)

print(f"  실제 모듈: {len(actual_modules)}개")

# SPEC에 있는 내부 모듈
spec_internal = set(categories.get('core', []) + 
                    categories.get('GUI', []) + 
                    categories.get('exchanges', []) +
                    categories.get('utils', []) +
                    categories.get('storage', []))

print(f"  SPEC 내부 모듈: {len(spec_internal)}개")

# 누락된 모듈
missing = actual_modules - spec_internal
if missing:
    print(f"\n  ⚠️ SPEC에 누락된 모듈 ({len(missing)}개):")
    for m in sorted(missing)[:15]:
        print(f"    - {m}")
    if len(missing) > 15:
        print(f"    ... 외 {len(missing) - 15}개")
else:
    print("  ✅ 모든 내부 모듈 포함됨")

# ============================================================
# [3] 필수 외부 패키지 확인
# ============================================================
print("\n[3] 필수 외부 패키지 확인")
print("-" * 50)

required_packages = [
    'ccxt', 'pandas', 'numpy', 'PyQt5', 'pyqtgraph',
    'ta', 'websocket', 'requests', 'cryptography',
    'pyarrow', 'sqlalchemy', 'aiohttp', 'orjson'
]

# 프로젝트에서 실제 import하는 패키지 수집
all_py = list(base.rglob('*.py'))
all_py = [f for f in all_py if '__pycache__' not in str(f) and '_backup' not in str(f)]

imported_packages = set()
for py_file in all_py:
    try:
        code = py_file.read_text(encoding='utf-8')
        # import xxx / from xxx import
        imports = re.findall(r'^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)', code, re.MULTILINE)
        imported_packages.update(imports)
    except Exception:

        pass

# 표준 라이브러리 제외
stdlib = {'os', 'sys', 'json', 'time', 'datetime', 'threading', 'asyncio', 
          'logging', 'pathlib', 'typing', 'collections', 'functools', 'itertools',
          'math', 'random', 'hashlib', 'base64', 'struct', 'copy', 'io', 'traceback',
          're', 'sqlite3', 'pickle', 'shutil', 'tempfile', 'subprocess', 'socket',
          'ssl', 'urllib', 'http', 'email', 'html', 'xml', 'csv', 'configparser',
          'argparse', 'abc', 'contextlib', 'dataclasses', 'enum', 'weakref', 'queue',
          'concurrent', 'multiprocessing', 'unittest', 'inspect', 'importlib', 'pkgutil',
          'platform', 'locale', 'calendar', 'zlib', 'gzip', 'bz2', 'lzma', 'zipfile',
          'tarfile', 'stat', 'fileinput', 'glob', 'fnmatch', 'linecache', 'textwrap',
          'difflib', 'secrets', 'hmac', 'uuid', 'decimal', 'fractions', 'statistics',
          'array', 'bisect', 'heapq', 'operator', 'string', 'codecs', 'unicodedata',
          'warnings', 'atexit', 'signal', 'errno', 'ctypes', 'mmap', 'select', 'selectors'}

external_imports = imported_packages - stdlib - {'core', 'GUI', 'exchanges', 'utils', 'storage'}

print(f"  프로젝트 외부 import: {len(external_imports)}개")

# SPEC에 누락된 외부 패키지
missing_external = []
for pkg in required_packages:
    if pkg not in hidden_imports and pkg not in spec_content:
        missing_external.append(pkg)

if missing_external:
    print(f"  ⚠️ 필수 패키지 누락: {missing_external}")
else:
    print("  ✅ 필수 패키지 모두 포함")

# ============================================================
# [4] 데이터 파일 확인
# ============================================================
print("\n[4] 데이터/리소스 파일 확인")
print("-" * 50)

required_data = [
    ('GUI/resources', '아이콘/이미지'),
    ('presets', '프리셋 JSON'),
    ('version.json', '버전 정보'),
]

for path, desc in required_data:
    full_path = base / path
    if full_path.exists():
        if full_path.is_dir():
            count = len(list(full_path.glob('*')))
            print(f"  ✅ {path}: {count}개 파일")
        else:
            print(f"  ✅ {path}")
    else:
        print(f"  ⚠️ {path} 없음 ({desc})")

# ============================================================
# [5] __init__.py 확인
# ============================================================
print("\n[5] __init__.py 확인")
print("-" * 50)

init_folders = ['core', 'GUI', 'exchanges', 'utils', 'storage']
for folder in init_folders:
    init_file = base / folder / '__init__.py'
    if init_file.exists():
        print(f"  ✅ {folder}/__init__.py")
    else:
        print(f"  ❌ {folder}/__init__.py 없음")

# ============================================================
# [6] Entry Point 확인
# ============================================================
print("\n[6] Entry Point 확인")
print("-" * 50)

# SPEC에서 entry point 추출
entry_match = re.search(r"Analysis\s*\(\s*\['([^']+)'", spec_content)
if entry_match:
    entry_point = entry_match.group(1)
    print(f"  Entry: {entry_point}")
    
    entry_path = base / entry_point
    if entry_path.exists():
        print(f"  ✅ 파일 존재")
    else:
        print(f"  ❌ 파일 없음")
else:
    print("  ⚠️ Entry point 파싱 실패")

# ============================================================
# [7] 최종 요약 및 권장사항
# ============================================================
print("\n" + "=" * 70)
print("📊 점검 결과 요약")
print("=" * 70)

issues = []

if missing:
    issues.append(f"내부 모듈 {len(missing)}개 누락")

if missing_external:
    issues.append(f"외부 패키지 누락: {missing_external}")

if issues:
    print(f"\n⚠️ 발견된 문제: {len(issues)}개")
    for issue in issues:
        print(f"  - {issue}")
    
    print("\n📋 SPEC 업데이트 필요")
    print("  자동 업데이트 스크립트 실행할까?")
else:
    print("\n✅ SPEC 구성 정상!")
    print("\n📦 빌드 진행:")
    print("  cd C:\\매매전략")
    print("  pyinstaller staru_clean.spec --noconfirm")

print("\n결과 공유해줘")
