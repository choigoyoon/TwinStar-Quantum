from pathlib import Path
import re
import py_compile

base = Path(__file__).parent

print('=' * 70)
print('🔍 전체 프로젝트 무결점 검사')
print('=' * 70)

all_issues = []

#############################################
# [1] 전체 파일 문법 검사
#############################################
print('\n📊 [1] 전체 문법 검사')

syntax_errors = []
all_py = [f for f in base.rglob('*.py') if '__pycache__' not in str(f)]

for f in all_py:
    try:
        py_compile.compile(str(f), doraise=True)
    except py_compile.PyCompileError as e:
        syntax_errors.append(f'{f.relative_to(base)}: {e}')

if syntax_errors:
    print(f'  ❌ 문법 오류: {len(syntax_errors)}개')
    for err in syntax_errors[:10]:
        print(f'    {err}')
    all_issues.extend(syntax_errors)
else:
    print(f'  ✅ 전체 {len(all_py)}개 파일 문법 정상')

#############################################
# [2] import 오류 가능성
#############################################
print('\n📊 [2] Import 오류 가능성')

import_issues = []
for f in all_py:
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            if line.strip().startswith('from ') or line.strip().startswith('import '):
                # 존재하지 않는 모듈 import 체크
                if 'core.' in line:
                    module = re.search(r'from (core\.\w+)', line)
                    if module:
                        mod_path = base / (module.group(1).replace('.', '/') + '.py')
                        if not mod_path.exists():
                            import_issues.append(f'{fname} L{i+1}: {line.strip()[:50]}')
    except Exception:

        pass

if import_issues:
    print(f'  ⚠️ Import 의심: {len(import_issues)}개')
    for issue in import_issues[:5]:
        print(f'    {issue}')
    all_issues.extend(import_issues)
else:
    print('  ✅ Import 문제 없음')

#############################################
# [3] None 체크 누락
#############################################
print('\n📊 [3] None 체크 누락')

none_issues = []
critical_patterns = [
    (r'self\.position\.', 'self.position'),
    (r'self\.exchange\.', 'self.exchange'),
    (r'self\.ws_handler\.', 'self.ws_handler'),
    (r'self\.bot\.', 'self.bot'),
]

for f in all_py:
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            for pattern, obj_name in critical_patterns:
                if re.search(pattern, line):
                    # 이전 5줄에 None 체크가 있는지
                    context = '\n'.join(lines[max(0,i-5):i+1])
                    if f'if {obj_name}' not in context and f'{obj_name} is not None' not in context:
                        if 'except' not in context and 'try' not in context:
                            none_issues.append(f'{fname} L{i+1}: {line.strip()[:50]}')
    except Exception:

        pass

if none_issues:
    print(f'  ⚠️ None 체크 누락 의심: {len(none_issues)}개')
    for issue in none_issues[:10]:
        print(f'    {issue}')
    if len(none_issues) > 10:
        print(f'    ... 외 {len(none_issues)-10}개')
else:
    print('  ✅ None 체크 문제 없음')

#############################################
# [4] except Exception: pass 남용
#############################################
print('\n📊 [4] except Exception: pass 남용')

pass_issues = []
for f in all_py:
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            if 'except' in line and ':' in line:
                next_line = lines[i+1].strip() if i+1 < len(lines) else ''
                if next_line == 'pass':
                    pass_issues.append(f'{fname} L{i+1}')
    except Exception:

        pass

if pass_issues:
    print(f'  ⚠️ except Exception: pass: {len(pass_issues)}개')
    for issue in pass_issues[:10]:
        print(f'    {issue}')
    if len(pass_issues) > 10:
        print(f'    ... 외 {len(pass_issues)-10}개')
else:
    print('  ✅ except Exception: pass 없음')

#############################################
# [5] DataFrame 위험 패턴
#############################################
print('\n📊 [5] DataFrame 위험 패턴')

df_issues = []
for f in all_py:
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            if re.search(r'if\s+\w*df\w*\s+(or|and)', line, re.I):
                if 'is None' not in line and 'is not None' not in line:
                    df_issues.append(f'{fname} L{i+1}: {line.strip()[:50]}')
    except Exception:

        pass

if df_issues:
    print(f'  ❌ DataFrame 위험: {len(df_issues)}개')
    for issue in df_issues:
        print(f'    {issue}')
    all_issues.extend(df_issues)
else:
    print('  ✅ DataFrame 패턴 정상')

#############################################
# [6] signal.get() 위험
#############################################
print('\n📊 [6] signal.get() 위험')

signal_issues = []
for f in all_py:
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            if 'signal.get(' in line.lower() and 'isinstance' not in line and 'getattr' not in line:
                signal_issues.append(f'{fname} L{i+1}: {line.strip()[:50]}')
    except Exception:

        pass

if signal_issues:
    print(f'  ⚠️ signal.get() 위험: {len(signal_issues)}개')
    for issue in signal_issues:
        print(f'    {issue}')
else:
    print('  ✅ signal.get() 정상')

#############################################
# [7] 하드코딩 경로
#############################################
print('\n📊 [7] 하드코딩 경로')

path_issues = []
for f in all_py:
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            if re.search(r'["\']C:\\\\', line) or re.search(r'["\']C:/', line):
                if '#' not in line.split('C:')[0]:
                    path_issues.append(f'{fname} L{i+1}: {line.strip()[:50]}')
    except Exception:

        pass

if path_issues:
    print(f'  ⚠️ 하드코딩 경로: {len(path_issues)}개')
    for issue in path_issues[:10]:
        print(f'    {issue}')
    if len(path_issues) > 10:
        print(f'    ... 외 {len(path_issues)-10}개')
else:
    print('  ✅ 하드코딩 경로 없음')

#############################################
# [8] float(dict) 위험
#############################################
print('\n📊 [8] float(dict) 위험')

float_issues = []
for f in all_py:
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            if re.search(r'float\s*\(\s*\w+\.get_balance', line):
                if 'safe_float' not in line:
                    float_issues.append(f'{fname} L{i+1}: {line.strip()[:50]}')
    except Exception:

        pass

if float_issues:
    print(f'  ❌ float(dict) 위험: {len(float_issues)}개')
    for issue in float_issues:
        print(f'    {issue}')
    all_issues.extend(float_issues)
else:
    print('  ✅ float 변환 정상')

#############################################
# [9] 레버리지 PnL 적용
#############################################
print('\n📊 [9] 레버리지 PnL 적용')

bot = base / 'core' / 'unified_bot.py'
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    lev_pnl = []
    for i, line in enumerate(lines):
        if 'pnl' in line.lower() and 'leverage' in line.lower():
            lev_pnl.append(f'L{i+1}: {line.strip()[:60]}')
    
    if lev_pnl:
        print(f'  ✅ 레버리지 PnL 적용: {len(lev_pnl)}곳')
    else:
        print('  ❌ 레버리지 PnL 적용 안 됨')
        all_issues.append('레버리지 PnL 미적용')

#############################################
# [10] 대시보드 연결 상태
#############################################
print('\n📊 [10] 대시보드 연결 상태')

dash = base / 'GUI' / 'trading_dashboard.py'
if dash.exists():
    code = dash.read_text(encoding='utf-8', errors='ignore')
    
    checks = {
        'QTimer': 'QTimer' in code,
        'update 함수': 'def update' in code or 'def _update' in code,
        'balance 조회': 'balance' in code.lower(),
        'position 조회': 'position' in code.lower(),
        'signal connect': '.connect(' in code,
    }
    
    for name, ok in checks.items():
        status = '✅' if ok else '❌'
        print(f'  {status} {name}')
        if not ok:
            all_issues.append(f'대시보드 {name} 누락')

#############################################
# 최종 요약
#############################################
print('\n' + '=' * 70)
print('📋 최종 요약')
print('=' * 70)

print(f'\n전체 파일: {len(all_py)}개')
print(f'문법 오류: {len(syntax_errors)}개')
print(f'DataFrame 위험: {len(df_issues)}개')
print(f'float(dict) 위험: {len(float_issues)}개')
print(f'None 체크 누락: {len(none_issues)}개')
print(f'except:pass: {len(pass_issues)}개')
print(f'하드코딩 경로: {len(path_issues)}개')

if all_issues:
    print(f'\n🔴 수정 필요: {len(all_issues)}개')
else:
    print('\n✅ 전체 무결점 통과!')
