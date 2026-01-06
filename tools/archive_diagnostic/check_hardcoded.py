import os

keywords = [
    'Quick', 'Deep', 'Standard', 'Run', 'Cancel', 'Search', 
    'Filter', 'Entry', 'Start', 'Stop', 'Save', 'Load',
    'Connect', 'Test', 'Download', 'Delete', 'Apply', 'Reset',
    'Previous', 'Next', 'Close', 'Success', 'Failed', 'Error',
    'Settings', 'Balance', 'Position', 'Order', 'Trade', 'Warning'
]

gui_files = [f for f in os.listdir('GUI') if f.endswith('.py')]

results = []
for fname in gui_files:
    try:
        with open(f'GUI/{fname}', 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if 't(' not in line and 'tr(' not in line and 'import' not in line and 'def ' not in line:
                for kw in keywords:
                    if f'"{kw}"' in line:
                        results.append(f'{fname}|L{i+1}|{kw}|{line.strip()[:70]}')
                        break
    except:
        pass

# Save to file
with open('hardcoded_list.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(results))

print(f'총 {len(results)}개 발견 → hardcoded_list.txt 저장됨')
for r in results:
    print(r)
