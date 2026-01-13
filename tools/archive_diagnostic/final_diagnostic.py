from pathlib import Path
import os
import json

base = Path(r'C:\매매전략')

print('='*60)
print('[1] 1000캔들 제한 위치 (1000, tail(, limit=)')
print('='*60)
for f in [base/'GUI'/'data_manager.py', base/'core'/'multi_sniper.py']:
    if not f.exists(): continue
    lines = f.read_text(encoding='utf-8', errors='ignore').split('\n')
    for i, line in enumerate(lines, 1):
        if any(k in line for k in ['1000', 'tail(', 'limit=']):
            if 'timestamp' not in line.lower():
                print(f'{f.relative_to(base)} L{i}: {line.strip()[:100]}')

print('\n' + '='*60)
print('[2] 프리셋 자동저장 위치 (save_preset, .json, dump()')
print('='*60)
targets = ['optimization_widget.py', 'backtest_widget.py', 'auto_optimizer.py', 'multi_sniper.py']
for f in base.rglob('*.py'):
    if '__pycache__' in str(f) or '.git' in str(f) or 'venv' in str(f): continue
    if f.name not in targets: continue
    try:
        lines = f.read_text(encoding='utf-8', errors='ignore').split('\n')
        for i, line in enumerate(lines, 1):
            if any(k in line for k in ['save_preset', 'presets/', '.json', 'dump(']):
                if '#' not in line.strip()[:2]: # 주석 제외
                    print(f'{f.relative_to(base)} L{i}: {line.strip()[:100]}')
    except Exception:

        pass

print('\n' + '='*60)
print('[3] trading_dashboard 레이아웃 (CoinRow, setFixedHeight, addStretch, setSizes)')
print('='*60)
f = base / 'GUI' / 'trading_dashboard.py'
if f.exists():
    lines = f.read_text(encoding='utf-8', errors='ignore').split('\n')
    for i, line in enumerate(lines, 1):
        if any(k in line for k in ['CoinRow', 'setFixedHeight', 'addStretch', 'setSizes', 'QVBoxLayout']):
            print(f'L{i}: {line.strip()[:100]}')

print('\n' + '='*60)
print('[4] 현재 프리셋 폴더 내용 (Top 20)')
print('='*60)
preset_dir = base / 'config' / 'presets'
if preset_dir.exists():
    p_files = sorted(list(preset_dir.glob('*.json')))
    for p in p_files[:20]:
        print(f'  {p.name}')
    if len(p_files) > 20:
        print(f'  ... 외 {len(p_files)-20}개')
else:
    print('❌ 프리셋 폴더 없음')
