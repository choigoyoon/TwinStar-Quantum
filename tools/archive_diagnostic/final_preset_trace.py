from pathlib import Path

base = Path(r'C:\매매전략')

print('=== 프리셋 자동저장 위치 (최적화 관련) ===')

for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or '.git' in str(f) or 'venv' in str(f): continue
    if 'optim' not in f.name.lower() and 'auto' not in f.name.lower(): continue
    
    try:
        lines = f.read_text(encoding='utf-8', errors='ignore').split('\n')
        for i, line in enumerate(lines, 1):
            if any(k in line for k in ['presets/', 'save_preset', 'wr_', '.json', 'dump(']):
                if '#' not in line.strip()[:2]:
                    print(f'{f.relative_to(base)} L{i}: {line.strip()[:100]}')
    except Exception:

        pass
