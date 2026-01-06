from pathlib import Path

f = Path(r'C:\매매전략\GUI\trading_dashboard.py')
lines = f.read_text(encoding='utf-8', errors='ignore').split('\n')

print('=== 매매 탭 레이아웃 구조 확인 ===\n')

print('[1] 개별 트레이딩 영역:')
for i, line in enumerate(lines):
    if 'single' in line.lower() or '개별' in line or 'control' in line.lower():
        print(f'  L{i+1}: {line.strip()[:70]}')

print('\n[2] 레이아웃 구조:')
for i, line in enumerate(lines):
    if 'Layout' in line and ('VBox' in line or 'HBox' in line or 'Grid' in line):
        print(f'  L{i+1}: {line.strip()[:70]}')

print('\n[3] addStretch / Spacer:')
for i, line in enumerate(lines):
    if 'addStretch' in line or 'Spacer' in line:
        print(f'  L{i+1}: {line.strip()[:70]}')
