import os

keywords = [
    'Quick', 'Deep', 'Standard', 'Run', 'Cancel', 'Search', 
    'Filter', 'Entry', 'Start', 'Stop', 'Save', 'Load',
    'Connect', 'Test', 'Download', 'Delete', 'Apply', 'Reset',
    'Previous', 'Next', 'Close', 'Success', 'Failed', 'Error',
    'Settings', 'Balance', 'Position', 'Order', 'Trade', 'Warning'
]

gui_files = [f for f in os.listdir('GUI') if f.endswith('.py')]
total = 0
remaining = []

for fname in gui_files:
    try:
        with open(f'GUI/{fname}', 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if 't(' not in line and 'tr(' not in line and 'import' not in line and 'def ' not in line:
                for kw in keywords:
                    if f'"{kw}"' in line:
                        total += 1
                        remaining.append(f'{fname}|L{i+1}|{kw}')
                        break
    except Exception:

        pass

if total == 0:
    print('✅ 모든 영어 텍스트 한글화 완료!')
else:
    print(f'⚠️ {total}개 남음:')
    for r in remaining[:10]:
        print(f'  {r}')
