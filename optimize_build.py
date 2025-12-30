from pathlib import Path
import re

base = Path(r'C:\매매전략')

print('=' * 70)
print('📦 빌드 설정 최적화')
print('=' * 70)

#############################################
# [1] 외부 패키지 수집
#############################################
print('\n[1] 외부 패키지 수집 중...')

all_imports = set()
for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        for m in re.findall(r'^import\s+([\w.]+)', code, re.MULTILINE):
            all_imports.add(m.split('.')[0])
        for m in re.findall(r'^from\s+([\w.]+)\s+import', code, re.MULTILINE):
            root = m.split('.')[0]
            if root not in ['core', 'exchanges', 'GUI', 'utils', 'storage']:
                all_imports.add(root)
    except:
        pass

# 표준 라이브러리 제외
stdlib = {'os', 'sys', 're', 'json', 'time', 'datetime', 'pathlib', 'logging',
          'threading', 'asyncio', 'hashlib', 'base64', 'collections', 'functools',
          'itertools', 'typing', 'dataclasses', 'enum', 'copy', 'math', 'random',
          'traceback', 'inspect', 'abc', 'contextlib', 'io', 'struct', 'socket',
          'ssl', 'http', 'urllib', 'email', 'html', 'xml', 'sqlite3', 'csv',
          'pickle', 'shelve', 'dbm', 'gzip', 'zipfile', 'tarfile', 'tempfile',
          'shutil', 'glob', 'fnmatch', 'linecache', 'tokenize', 'keyword',
          'warnings', 'weakref', 'types', 'operator', 'string', 'textwrap',
          'unicodedata', 'locale', 'gettext', 'argparse', 'configparser',
          'queue', 'sched', 'signal', 'mmap', 'ctypes', 'multiprocessing',
          'subprocess', 'concurrent', 'platform', 'uuid', 'secrets', 'hmac',
          'binascii', 'codecs', 'encodings', 'importlib', 'pkgutil', 'unittest',
          'doctest', 'pdb', 'profile', 'timeit', 'trace', 'gc', 'dis', 'ast',
          'builtins', 'errno', 'stat', 'posixpath', 'ntpath', 'genericpath',
          'heapq', 'bisect', 'array', 'numbers', 'decimal', 'fractions',
          'statistics', 'cmath', 'zlib', 'bz2', 'lzma', 'atexit', 'sysconfig'}

external = sorted(all_imports - stdlib - {'', 'core', 'exchanges', 'GUI', 'utils', 'storage'})
print(f'  외부 패키지: {len(external)}개')

#############################################
# [2] __init__.py 생성/확인
#############################################
print('\n[2] __init__.py 점검/생성')

folders = ['core', 'exchanges', 'GUI', 'utils', 'storage']
for folder in folders:
    init_file = base / folder / '__init__.py'
    if not init_file.exists():
        init_file.write_text('# Auto-generated\n', encoding='utf-8')
        print(f'  ✅ {folder}/__init__.py 생성')
    else:
        print(f'  ⚪ {folder}/__init__.py 존재')

#############################################
# [3] spec 파일 업데이트
#############################################
print('\n[3] staru_clean.spec 업데이트')

spec_file = base / 'staru_clean.spec'
if not spec_file.exists():
    print('  ❌ staru_clean.spec 없음')
else:
    spec = spec_file.read_text(encoding='utf-8', errors='ignore')
    
    # 기존 hiddenimports 추출
    hidden_match = re.search(r'hiddenimports\s*=\s*\[(.*?)\]', spec, re.DOTALL)
    existing = set()
    if hidden_match:
        existing = set(re.findall(r"'([^']+)'", hidden_match.group(1)))
    
    # 추가할 패키지
    to_add = []
    for pkg in external:
        if pkg not in existing and pkg.lower() not in [e.lower() for e in existing]:
            to_add.append(pkg)
    
    # 내부 모듈 추가
    internal_modules = [
        'core.unified_bot',
        'core.strategy_core',
        'core.multi_sniper',
        'core.license_guard',
        'exchanges.exchange_manager',
        'exchanges.bybit_exchange',
        'exchanges.binance_exchange',
        'exchanges.ws_handler',
        'GUI.staru_main',
        'GUI.trading_dashboard',
        'GUI.backtest_widget',
        'GUI.settings_widget',
        'utils.data_manager',
        'storage.trade_storage',
        'storage.trade_history',
    ]
    
    for mod in internal_modules:
        if mod not in existing:
            to_add.append(mod)
    
    if to_add:
        print(f'  추가할 항목: {len(to_add)}개')
        
        # 새 hiddenimports 생성
        all_hidden = sorted(existing | set(to_add))
        new_hidden = 'hiddenimports=[\n'
        for h in all_hidden:
            new_hidden += f"        '{h}',\n"
        new_hidden += '    ]'
        
        # 교체
        if hidden_match:
            new_spec = spec[:hidden_match.start()] + new_hidden + spec[hidden_match.end():]
        else:
            # hiddenimports가 없으면 Analysis 뒤에 추가
            new_spec = spec.replace('Analysis(', f'Analysis(\n    {new_hidden},\n    ')
        
        # 백업 및 저장
        backup = spec_file.with_suffix('.spec.bak')
        backup.write_text(spec, encoding='utf-8')
        spec_file.write_text(new_spec, encoding='utf-8')
        
        print(f'  ✅ spec 업데이트 완료 (백업: {backup.name})')
        print(f'  📝 추가된 항목:')
        for item in to_add[:15]:
            print(f'      - {item}')
        if len(to_add) > 15:
            print(f'      ... 외 {len(to_add)-15}개')
    else:
        print('  ✅ 모든 패키지 이미 포함됨')

#############################################
# [4] 최종 확인
#############################################
print('\n' + '=' * 70)
print('📊 완료')
print('=' * 70)
print('  다음 명령어로 빌드:')
print('    cd C:\\매매전략')
print('    pyinstaller staru_clean.spec --noconfirm')
print('=' * 70)
