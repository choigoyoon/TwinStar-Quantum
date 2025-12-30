from pathlib import Path
import re

base = Path(r'C:\매매전략')

print('=' * 70)
print('💳 결제 시스템 아키텍처 검증')
print('=' * 70)

#############################################
# [1] 파일 존재 여부
#############################################
print('\n📁 [1] 파일 존재 여부')

files_to_check = {
    'pc_license_dialog.py': '로그인/인증',
    'payment_dialog.py': '결제 다이얼로그',
    'unified_bot.py': '등급 제한 체크',
    'staru_main.py': '등급 표시',
}

found_files = {}
for f in base.rglob('*.py'):
    if '__pycache__' not in str(f):
        for target in files_to_check:
            if f.name == target:
                found_files[target] = f

for fname, desc in files_to_check.items():
    if fname in found_files:
        print(f'  ✅ {fname} ({desc})')
    else:
        print(f'  ❌ {fname} ({desc}) - 없음')

#############################################
# [2] 핵심 기능 구현 확인
#############################################
print('\n🔧 [2] 핵심 기능 구현 확인')

checks = {
    'TIER_LIMITS': ('unified_bot.py', 'TIER_LIMITS'),
    'hw_id / hardware_id': ('*', 'hw_id|hardware_id|get_hardware_id'),
    'create_upgrade_session': ('*', 'create_upgrade_session'),
    'webbrowser.open': ('*', 'webbrowser.open'),
    'tier 체크': ('unified_bot.py', 'tier|_check_tier'),
    'license API': ('*', 'license.php|license_api'),
    'session_id': ('*', 'session_id'),
    'days_left': ('*', 'days_left|days_remaining'),
    'expires': ('*', 'expires|expir'),
}

for check_name, (target_file, pattern) in checks.items():
    found = False
    locations = []
    
    search_files = found_files.values() if target_file == '*' else [found_files.get(target_file)]
    search_files = [f for f in search_files if f]
    
    if not search_files:
        search_files = [f for f in base.rglob('*.py') if '__pycache__' not in str(f)]
    
    for f in search_files:
        try:
            code = f.read_text(encoding='utf-8', errors='ignore')
            if re.search(pattern, code, re.I):
                found = True
                locations.append(f.name)
        except:
            pass
    
    if found:
        print(f'  ✅ {check_name}: {", ".join(list(set(locations))[:3])}')
    else:
        print(f'  ❌ {check_name}: 없음')

#############################################
# [3] 등급 제한 로직 상세
#############################################
print('\n📊 [3] 등급 제한 로직 상세')

if 'unified_bot.py' in found_files:
    code = found_files['unified_bot.py'].read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    # TIER_LIMITS 찾기
    in_tier = False
    tier_code = []
    for i, line in enumerate(lines):
        if 'TIER_LIMITS' in line and '=' in line:
            in_tier = True
        if in_tier:
            tier_code.append(f'L{i+1}: {line}')
            if '}' in line and line.count('}') >= 2:
                break
    
    if tier_code:
        print('  TIER_LIMITS 정의:')
        for t in tier_code[:15]:
            print(f'    {t}')
    else:
        print('  ❌ TIER_LIMITS 정의 없음')
    
    # _check_tier 함수 찾기
    for i, line in enumerate(lines):
        if 'def ' in line and 'tier' in line.lower() and 'check' in line.lower():
            print(f'\n  등급 체크 함수: L{i+1}: {line.strip()}')

#############################################
# [4] 결제 흐름 구현 확인
#############################################
print('\n💰 [4] 결제 흐름 구현 확인')

payment_features = {
    'upgrade 버튼': 'upgrade|업그레이드',
    'session 생성': 'create.*session|session.*create',
    'webbrowser': 'webbrowser',
    '결제 완료 안내': '결제.*완료|재시작',
    'API URL': 'youngstreet|api.*license|license.*api',
}

for feat, pattern in payment_features.items():
    found_in = []
    for f in base.rglob('*.py'):
        if '__pycache__' in str(f):
            continue
        try:
            code = f.read_text(encoding='utf-8', errors='ignore')
            if re.search(pattern, code, re.I):
                found_in.append(f.name)
        except:
            pass
    
    if found_in:
        print(f'  ✅ {feat}: {", ".join(list(set(found_in))[:3])}')
    else:
        print(f'  ❌ {feat}: 미구현')

#############################################
# [5] 요약
#############################################
print('\n' + '=' * 70)
print('📋 검증 요약')
print('=' * 70)
