from pathlib import Path
import re
import ast

base = Path(__file__).parent

print('=' * 70)
print('📦 TwinStar Quantum 빌드 전 전체 점검')
print('=' * 70)

#############################################
# [1] SPEC 파일 분석
#############################################
print('\n📋 [1] SPEC 파일 분석')
print('-' * 70)

spec_file = base / 'staru_clean.spec'
if spec_file.exists():
    spec = spec_file.read_text(encoding='utf-8', errors='ignore')
    
    # hiddenimports 추출
    hidden_match = re.search(r'hiddenimports\s*=\s*\[(.*?)\]', spec, re.DOTALL)
    if hidden_match:
        hidden_raw = hidden_match.group(1)
        hidden_imports = re.findall(r"'([^']+)'", hidden_raw)
        print(f'  hiddenimports: {len(hidden_imports)}개')
        for h in hidden_imports[:10]:
            print(f'    - {h}')
        if len(hidden_imports) > 10:
            print(f'    ... 외 {len(hidden_imports)-10}개')
    
    # datas 추출
    datas_match = re.search(r'datas\s*=\s*\[(.*?)\]', spec, re.DOTALL)
    if datas_match:
        datas_raw = datas_match.group(1)
        datas = re.findall(r"\('([^']+)'", datas_raw)
        print(f'\n  datas: {len(datas)}개')
        for d in datas[:5]:
            print(f'    - {d}')
else:
    print('  ❌ staru_clean.spec 없음')

#############################################
# [2] 프로젝트 전체 Import 수집
#############################################
print('\n📋 [2] 프로젝트 Import 분석')
print('-' * 70)

all_imports = set()
internal_modules = set()

for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        
        # import xxx
        for m in re.findall(r'^import\s+([\w.]+)', code, re.MULTILINE):
            all_imports.add(m.split('.')[0])
        
        # from xxx import
        for m in re.findall(r'^from\s+([\w.]+)\s+import', code, re.MULTILINE):
            root = m.split('.')[0]
            if root in ['core', 'exchanges', 'GUI', 'utils', 'storage']:
                internal_modules.add(m)
            else:
                all_imports.add(root)
    except Exception:

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
          'doctest', 'pdb', 'profile', 'timeit', 'trace', 'gc', 'dis', 'ast'}

external = all_imports - stdlib - {'core', 'exchanges', 'GUI', 'utils', 'storage', ''}
print(f'  외부 패키지: {len(external)}개')
for e in sorted(external):
    print(f'    - {e}')

#############################################
# [3] SPEC에 누락된 패키지 확인
#############################################
print('\n📋 [3] SPEC에 누락된 패키지')
print('-' * 70)

if spec_file.exists():
    spec_lower = spec.lower()
    missing = []
    for pkg in external:
        if pkg.lower() not in spec_lower:
            missing.append(pkg)
    
    if missing:
        print(f'  ⚠️ hiddenimports에 추가 권장: {len(missing)}개')
        for m in missing:
            print(f'    - {m}')
    else:
        print('  ✅ 모든 외부 패키지 포함됨')

#############################################
# [4] 내부 모듈 연결 확인
#############################################
print('\n📋 [4] 내부 모듈 연결')
print('-' * 70)

# 각 폴더별 모듈 존재 확인
folders = ['core', 'exchanges', 'GUI', 'utils', 'storage']
for folder in folders:
    p = base / folder
    if p.exists():
        py_files = list(p.glob('*.py'))
        init_exists = (p / '__init__.py').exists()
        init_mark = '✅' if init_exists else '❌'
        print(f'  {folder}/: {len(py_files)}개 파일, __init__.py: {init_mark}')
    else:
        print(f'  ❌ {folder}/ 없음')

#############################################
# [5] 누락된 기능 체크
#############################################
print('\n📋 [5] 기능 구현 체크')
print('-' * 70)

features = {
    # 거래소
    'Bybit 연동': ('exchanges/bybit_exchange.py', ['place_order', 'get_position']),
    'Binance 연동': ('exchanges/binance_exchange.py', ['place_order', 'get_position']),
    'Upbit 연동': ('exchanges/upbit_exchange.py', ['place_order', 'get_balance']),
    'WebSocket': ('exchanges/ws_handler.py', ['connect', 'on_message']),
    
    # 코어
    '매매 봇': ('core/unified_bot.py', ['execute_entry', '_close_on_sl']),
    '전략 엔진': ('core/strategy_core.py', ['detect_pattern', 'calculate_rsi']),
    '멀티 스캐너': ('core/multi_sniper.py', ['scan', 'on_signal']),
    
    # GUI
    '메인 윈도우': ('GUI/staru_main.py', ['QMainWindow', 'show']),
    '대시보드': ('GUI/trading_dashboard.py', ['refresh', 'update']),
    '백테스트': ('GUI/backtest_widget.py', ['run_backtest', 'result']),
    '설정': ('GUI/settings_widget.py', ['save', 'load']),
    
    # 데이터
    '데이터 매니저': ('utils/data_manager.py', ['load', 'save', 'parquet']),
    '거래 저장소': ('storage/trade_storage.py', ['add_trade', 'get_trades']),
}

for feat, (fpath, keywords) in features.items():
    f = base / fpath
    if f.exists():
        code = f.read_text(encoding='utf-8', errors='ignore').lower()
        found = sum(1 for k in keywords if k.lower() in code)
        if found == len(keywords):
            print(f'  ✅ {feat}')
        else:
            print(f'  ⚠️ {feat}: {found}/{len(keywords)} 키워드')
    else:
        print(f'  ❌ {feat}: 파일 없음')

#############################################
# [6] 데이터 파일 확인
#############################################
print('\n📋 [6] 데이터/리소스 파일')
print('-' * 70)

resources = [
    'version.json',
    'staru_clean.spec',
    'requirements.txt',
    'GUI/resources',
    'data/cache',
]

for res in resources:
    p = base / res
    if p.exists():
        if p.is_dir():
            count = len(list(p.glob('*')))
            print(f'  ✅ {res}/ ({count}개 파일)')
        else:
            print(f'  ✅ {res}')
    else:
        print(f'  ⚠️ {res}: 없음')

#############################################
# [7] 최종 요약
#############################################
print('\n' + '=' * 70)
print('📊 최종 요약')
print('=' * 70)
print(f'  외부 패키지: {len(external)}개')
print(f'  내부 모듈: {len(internal_modules)}개')
print(f'  SPEC 누락: {len(missing) if "missing" in (" " + "missing") else "N/A"}개')
print('=' * 70)
