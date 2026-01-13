from pathlib import Path

base = Path(r'C:\매매전략')

print('=== 프리셋 자동저장 위치 탐색 (Backtest/Strategy) ===')

# 백테스트 관련 파일들
targets = ['backtest_widget.py', 'backtest_runner.py', 'strategy_core.py', 'unified_bot.py']

for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or '.git' in str(f) or 'venv' in str(f): continue
    if not any(t in f.name for t in targets): continue
    
    try:
        lines = f.read_text(encoding='utf-8', errors='ignore').split('\n')
        for i, line in enumerate(lines, 1):
            if any(k in line.lower() for k in ['presets/', 'save_preset', 'to_json', 'dump(', '.json']):
                if 'load' not in line.lower() and 'read' not in line.lower() and '#' not in line.strip()[:2]:
                    print(f'{f.relative_to(base)} L{i}: {line.strip()[:100]}')
    except Exception:

        pass

print('\n=== config/presets 폴더에 쓰는 코드 전체 검색 ===')
for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or '.git' in str(f) or 'venv' in str(f): continue
    try:
        content = f.read_text(encoding='utf-8', errors='ignore')
        if 'presets' in content and ('write' in content or 'dump' in content or 'save' in content):
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                if 'presets' in line and (any(k in line for k in ['write', 'dump', 'open', 'save', 'Path'])):
                    if '#' not in line.strip()[:2]:
                        print(f'{f.relative_to(base)} L{i}: {line.strip()[:100]}')
    except Exception:

        pass
