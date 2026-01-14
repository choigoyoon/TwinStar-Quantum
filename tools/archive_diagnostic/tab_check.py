from pathlib import Path
import re

base = Path(__file__).parent

print('=' * 70)
print('🔗 각 탭 ↔ Python 파일 연결 체크')
print('=' * 70)

#############################################
# [1] 메인 윈도우 - 탭 구조 확인
#############################################
print('\n📌 [1] 메인 윈도우 탭 구조')

main = base / 'GUI' / 'staru_main.py'
if main.exists():
    code = main.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print(f'\n  파일: GUI/staru_main.py ({len(lines)}줄)')
    
    # 탭 위젯 import 찾기
    print('\n  [Import된 위젯]:')
    for i, line in enumerate(lines):
        if 'import' in line and ( 'widget' in line.lower() or 'dashboard' in line.lower() ):
            print(f'    L{i+1}: {line.strip()[:70]}')
        if 'from' in line and 'GUI' in line:
            print(f'    L{i+1}: {line.strip()[:70]}')
    
    # addTab 찾기
    print('\n  [탭 추가 (addTab)]:')
    for i, line in enumerate(lines):
        if 'addTab' in line or 'add_tab' in line.lower():
            print(f'    L{i+1}: {line.strip()[:70]}')

#############################################
# [2] 각 탭별 위젯 파일 존재 확인
#############################################
print('\n📌 [2] 탭별 위젯 파일')

tab_files = {
    '매매': ['trading_dashboard.py', 'dashboard_widget.py'],
    '설정': ['settings_widget.py'],
    '수집': ['data_collector_widget.py', 'data_widget.py'],
    '백테스트': ['backtest_widget.py'],
    '최적화': ['optimization_widget.py'],
    '결과': ['results_widget.py', 'result_widget.py'],
    '거래내역': ['trade_history_widget.py', 'history_widget.py'],
}

gui_path = base / 'GUI'

for tab_name, possible_files in tab_files.items():
    found = None
    for fname in possible_files:
        f = gui_path / fname
        if f.exists():
            found = f
            break
    
    if found:
        code = found.read_text(encoding='utf-8', errors='ignore')
        lines = len(code.split('\n'))
        
        # 클래스 이름 찾기
        import re
        classes = re.findall(r'class\s+(\w+)', code)
        
        print(f'\n  ✅ {tab_name} 탭')
        print(f'     파일: {found.name} ({lines}줄)')
        print(f'     클래스: {classes[:3]}')
        
        # 주요 함수 찾기
        funcs = re.findall(r'def\s+(\w+)\(self', code)
        key_funcs = [f for f in funcs if any(k in f.lower() for k in ['init', 'start', 'stop', 'run', 'execute', 'update', 'refresh', 'load', 'save', 'setup'])]
        print(f'     주요 함수: {key_funcs[:5]}')
    else:
        print(f'\n  ❌ {tab_name} 탭 - 파일 없음 (검색: {possible_files})')

#############################################
# [3] 탭 → Core 연결 확인
#############################################
print('\n📌 [3] 탭 → Core 모듈 연결')

connections = {
    'trading_dashboard.py': ['unified_bot', 'UnifiedBot'],
    'backtest_widget.py': ['strategy_core', 'AlphaX7'],
    'optimization_widget.py': ['strategy_core', 'AlphaX7'],
    'settings_widget.py': ['exchange_manager', 'ExchangeManager'],
    'data_collector_widget.py': ['data_manager', 'DataManager'], # fallback to data_widget below
}

# Add data_widget.py to connections as it's the more likely name based on file list
connections['data_widget.py'] = ['data_manager', 'DataManager', 'Downloader']

for widget_file, core_modules in connections.items():
    f = gui_path / widget_file
    if f.exists():
        code = f.read_text(encoding='utf-8', errors='ignore')
        
        found_modules = []
        for mod in core_modules:
            if mod in code:
                found_modules.append(mod)
        
        if found_modules:
            print(f'  ✅ {widget_file} → {found_modules}')
        else:
            print(f'  ⚠️ {widget_file} → Core 연결 없음')
    else:
        # Don't print for files that just don't exist from the candidates
        pass

#############################################
# [4] 각 위젯의 버튼/시그널 확인
#############################################
print('\n📌 [4] 위젯별 버튼/시그널')

for widget_file in ['trading_dashboard.py', 'backtest_widget.py', 'optimization_widget.py', 'settings_widget.py', 'data_widget.py']:
    f = gui_path / widget_file
    if f.exists():
        code = f.read_text(encoding='utf-8', errors='ignore')
        
        # 버튼 찾기
        buttons = re.findall(r'QPushButton\(["\']([^"\']+)["\']', code)
        
        # 시그널 연결 찾기
        connects = len(re.findall(r'\.connect\(', code))
        
        # clicked 연결
        clicked = re.findall(r'\.clicked\.connect\(self\.(\w+)\)', code)
        
        print(f'\n  {widget_file}:')
        print(f'    버튼: {buttons[:5]}{"..." if len(buttons) > 5 else ""}')
        print(f'    시그널 연결: {connects}개')
        print(f'    클릭 핸들러: {clicked[:5]}')

#############################################
# [5] 데이터 흐름 확인
#############################################
print('\n📌 [5] 데이터 흐름 (Parquet/JSON)')

for widget_file in gui_path.glob('*.py'):
    if '__pycache__' in str(widget_file):
        continue
    
    code = widget_file.read_text(encoding='utf-8', errors='ignore')
    
    has_parquet = 'parquet' in code.lower()
    has_json = 'json' in code.lower() and ('load' in code.lower() or 'save' in code.lower())
    
    if has_parquet or has_json:
        data_types = []
        if has_parquet:
            data_types.append('Parquet')
        if has_json:
            data_types.append('JSON')
        print(f'  {widget_file.name}: {", ".join(data_types)}')

print('\n' + '=' * 70)
print('📋 완료')
print('=' * 70)
