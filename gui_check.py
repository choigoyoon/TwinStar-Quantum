from pathlib import Path
import ast
import re

base = Path(r'C:\매매전략\GUI')

print('=' * 60)
print('🔍 GUI 버튼/기능 연동 전체 검증')
print('=' * 60)

results = {
    'import_errors': [],
    'button_no_connect': [],
    'missing_handlers': [],
    'none_risks': []
}

# [1] 각 위젯 파일별 검사
widgets = [
    'trading_dashboard.py',
    'settings_widget.py', 
    'data_collector_widget.py',
    'backtest_widget.py',
    'optimization_widget.py',
    'staru_main.py'
]

for widget_name in widgets:
    f = base / widget_name
    if not f.exists():
        print(f'\n❌ {widget_name} - 파일 없음!')
        continue
    
    print(f'\n{"="*50}')
    print(f'📄 {widget_name}')
    print(f'{"="*50}')
    
    code = f.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    # [A] Import 검사
    print('\n[A] Import 검사:')
    imports = []
    for i, line in enumerate(lines):
        if line.strip().startswith('from ') or line.strip().startswith('import '):
            if any(x in line for x in ['core.', 'exchanges.', 'utils.', 'storage.']):
                imports.append((i+1, line.strip()[:60]))
    
    for ln, imp in imports[:5]:
        print(f'  L{ln}: {imp}')
    if len(imports) > 5:
        print(f'  ... +{len(imports)-5}개')
    
    # [B] 버튼 생성 vs 연결 검사
    print('\n[B] 버튼 연결 검사:')
    buttons = []
    connects = []
    
    for i, line in enumerate(lines):
        # 버튼 생성
        if 'QPushButton' in line and '=' in line:
            match = re.search(r'self\.(\w+)\s*=\s*QPushButton', line)
            if match:
                buttons.append((match.group(1), i+1))
        
        # 연결
        if '.clicked.connect' in line:
            match = re.search(r'self\.(\w+)\.clicked\.connect', line)
            if match:
                connects.append(match.group(1))
    
    connected_btns = set(connects)
    for btn_name, ln in buttons:
        status = '✅' if btn_name in connected_btns else '⚠️ 미연결'
        print(f'  {status} {btn_name} (L{ln})')
        if btn_name not in connected_btns:
            results['button_no_connect'].append(f'{widget_name}: {btn_name}')
    
    # [C] 핸들러 함수 존재 확인
    print('\n[C] 핸들러 함수 검사:')
    handlers = set()
    missing = []
    
    for i, line in enumerate(lines):
        if '.connect(self.' in line:
            match = re.search(r'\.connect\(self\.(\w+)\)', line)
            if match:
                handler = match.group(1)
                handlers.add(handler)
    
    for handler in handlers:
        # 함수 정의 찾기
        pattern = f'def {handler}\\s*\\('
        if re.search(pattern, code):
            print(f'  ✅ {handler}()')
        else:
            print(f'  ❌ {handler}() - 정의 없음!')
            missing.append(f'{widget_name}: {handler}')
            results['missing_handlers'].append(f'{widget_name}: {handler}')
    
    # [D] None 위험 체크
    print('\n[D] None 위험 패턴:')
    none_risks = 0
    for i, line in enumerate(lines):
        # self.xxx.method() 패턴에서 xxx가 None일 수 있는 경우
        if re.search(r'self\.\w+\.\w+\(', line) and 'if ' not in line and 'hasattr' not in line:
            if any(risk in line for risk in ['self.bot.', 'self.exchange.', 'self.logger.', 'self.thread.']):
                if none_risks < 3:
                    print(f'  ⚠️ L{i+1}: {line.strip()[:50]}')
                none_risks += 1
    if none_risks > 3:
        print(f'  ... +{none_risks-3}개 추가')

# [2] 모듈 Import 테스트
print('\n' + '=' * 60)
print('🔌 실제 Import 테스트')
print('=' * 60)

import sys
project_root = str(base.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

test_modules = [
    ('GUI.trading_dashboard', 'TradingDashboard'),
    ('GUI.settings_widget', 'SettingsWidget'),
    ('GUI.backtest_widget', 'BacktestWidget'),
    ('GUI.data_collector_widget', 'DataCollectorWidget'),
    ('core.unified_bot', 'UnifiedBot'),
    ('core.strategy_core', 'AlphaX7Core'),
    ('exchanges.exchange_manager', 'ExchangeManager'),
]

for mod_path, class_name in test_modules:
    try:
        mod = __import__(mod_path, fromlist=[class_name])
        cls = getattr(mod, class_name, None)
        if cls:
            print(f'  ✅ {mod_path}.{class_name}')
        else:
            print(f'  ⚠️ {mod_path} - {class_name} 클래스 없음')
    except Exception as e:
        err_short = str(e)[:50]
        print(f'  ❌ {mod_path}: {err_short}')
        results['import_errors'].append(f'{mod_path}: {e}')

# [3] 요약
print('\n' + '=' * 60)
print('📊 검증 요약')
print('=' * 60)
print(f"Import 에러: {len(results['import_errors'])}건")
print(f"미연결 버튼: {len(results['button_no_connect'])}건")
print(f"누락 핸들러: {len(results['missing_handlers'])}건")

if results['import_errors']:
    print('\n🔴 Import 에러 상세:')
    for e in results['import_errors']:
        print(f'  - {e}')

if results['missing_handlers']:
    print('\n🔴 누락 핸들러 상세:')
    for h in results['missing_handlers']:
        print(f'  - {h}')
