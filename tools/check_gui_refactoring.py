import sys
import os
import inspect
sys.path.insert(0, r'C:\매매전략')

print('=' * 60)
print('=== GUI 리팩토링 영향 분석 ===')
print('=' * 60)
print()

# 1. 분리된 컴포넌트 확인
print('[1] 분리된 GUI 컴포넌트 현황')
print('-' * 40)

components = {
    'GUI/components/__init__.py': ['PositionTable', 'BotControlCard', 'RiskHeaderWidget', 'ExternalDataWorker'],
    'GUI/components/position_table.py': ['PositionTable'],
    'GUI/components/bot_control_card.py': ['BotControlCard'],
    'GUI/components/market_status.py': ['RiskHeaderWidget'],
    'GUI/components/workers.py': ['ExternalDataWorker'],
    'GUI/components/interactive_chart.py': ['InteractiveChart', 'EquityCurveChart']
}

missing_files = []
missing_classes = []

for filepath, classes in components.items():
    full_path = os.path.join(r'C:\매매전략', filepath)
    if os.path.exists(full_path):
        print(f'✅ {filepath}')
        # Check if classes exist
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        for cls in classes:
            if f'class {cls}' in content or f'from ' in content and cls in content:
                print(f'    ✅ {cls}')
            else:
                print(f'    ❌ {cls} (Missing or not exported)')
                missing_classes.append(f'{filepath}:{cls}')
    else:
        print(f'❌ {filepath} (File Missing!)')
        missing_files.append(filepath)

print()

# 2. 주요 GUI 파일의 Import 상태
print('[2] 주요 GUI 파일 Import 상태')
print('-' * 40)

main_gui_files = [
    ('GUI/trading_dashboard.py', ['PositionTable', 'BotControlCard', 'RiskHeaderWidget', 'ExternalDataWorker']),
    ('GUI/backtest_widget.py', ['InteractiveChart', 'EquityCurveChart']),
    ('GUI/optimization_widget.py', ['OptimizationEngine']),
    ('GUI/staru_main.py', [])
]

import_issues = []

for filepath, expected_imports in main_gui_files:
    full_path = os.path.join(r'C:\매매전략', filepath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f'{filepath}:')
        
        # Check for GUI.components imports
        if 'from GUI.components' in content or 'from .components' in content:
            print('  ✅ GUI.components import 있음')
        elif expected_imports:
            print('  ⚠️ GUI.components import 없음 (필요할 수 있음)')
        
        # Check for class definitions that should have been removed
        for cls in expected_imports:
            if f'class {cls}(' in content or f'class {cls}:' in content:
                print(f'  ❌ {cls} 클래스가 아직 정의되어 있음! (중복)')
                import_issues.append(f'{filepath}: {cls} 중복 정의')
            else:
                print(f'  ✅ {cls} 분리됨 (정의 없음)')
    else:
        print(f'❌ {filepath} 파일 없음!')

print()

# 3. 파일 크기 비교
print('[3] 주요 파일 크기 (리팩토링 결과)')
print('-' * 40)

size_check = [
    ('GUI/trading_dashboard.py', 2500),  # Should be reduced from ~4000+ 
    ('GUI/backtest_widget.py', 2000),
    ('GUI/optimization_widget.py', 2000),
    ('core/unified_bot.py', 500)
]

for filepath, target_max in size_check:
    full_path = os.path.join(r'C:\매매전략', filepath)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as f:
            lines = len(f.readlines())
        status = '✅' if lines <= target_max else '⚠️'
        print(f'{status} {filepath}: {lines}줄 (목표: <{target_max})')
    else:
        print(f'❌ {filepath} 없음')

print()

# 4. GUI 로딩 테스트
print('[4] GUI 모듈 Import 테스트')
print('-' * 40)

gui_modules = [
    'GUI.components',
    'GUI.components.position_table',
    'GUI.components.bot_control_card',
    'GUI.components.market_status',
    'GUI.components.workers',
    'GUI.components.interactive_chart',
    'GUI.trading_dashboard',
    'GUI.backtest_widget',
    'GUI.optimization_widget'
]

import_errors = []

for mod in gui_modules:
    try:
        __import__(mod)
        print(f'✅ {mod}')
    except Exception as e:
        print(f'❌ {mod}: {str(e)[:50]}')
        import_errors.append(f'{mod}: {e}')

print()

# 5. 요약
print('=' * 60)
print('=== 요약 ===')
print('=' * 60)

if missing_files:
    print(f'❌ 누락된 파일: {len(missing_files)}개')
    for f in missing_files:
        print(f'   - {f}')
        
if missing_classes:
    print(f'❌ 누락된 클래스: {len(missing_classes)}개')
    for c in missing_classes:
        print(f'   - {c}')

if import_issues:
    print(f'⚠️ 중복 정의: {len(import_issues)}개')
    for i in import_issues:
        print(f'   - {i}')

if import_errors:
    print(f'❌ Import 에러: {len(import_errors)}개')
    for e in import_errors:
        print(f'   - {e}')

if not (missing_files or missing_classes or import_issues or import_errors):
    print('✅ 모든 GUI 리팩토링 정상!')
else:
    print()
    print('→ 위 문제들을 수정해야 합니다.')
