import os

# 수집 탭 + 백테스트 탭 영어 텍스트 검색
keywords = [
    'Data', 'Collector', 'Download', 'Symbol', 'Select', 'All', 'Clear',
    'Custom', 'Add', 'Remove', 'Start', 'Stop', 'Status', 'Progress',
    'Backtest', 'Results', 'Trade', 'Win', 'Loss', 'Profit', 'Return',
    'Preset', 'Load', 'Save', 'Delete', 'Refresh', 'Run', 'Cancel',
    'Exchange', 'Timeframe', 'Period', 'From', 'To', 'Capital', 'Leverage',
    'No data', 'Chart', 'Table', 'Entry', 'Exit', 'PnL', 'Total',
    'Filter', 'Trend', 'Mode', 'Quick', 'Standard', 'Deep'
]

files = ['GUI/data_collector_widget.py', 'GUI/backtest_widget.py', 'GUI/data_download_widget.py']

print('=== 수집/백테스트 탭 영어 텍스트 검색 ===\n')
for fpath in files:
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    found = []
    for i, line in enumerate(lines):
        if 't(' not in line and 'import' not in line and 'def ' not in line and '#' not in line:
            for kw in keywords:
                # UI 텍스트로 보이는 패턴만 검색
                if f'"{kw}"' in line or f"'{kw}'" in line or f'("{kw}' in line:
                    found.append(f'  L{i+1}: {line.strip()[:55]}')
                    break
    
    if found:
        print(f'--- {os.path.basename(fpath)} ({len(found)}개) ---')
        for f in found[:15]:
            print(f)
        if len(found) > 15:
            print(f'  ... +{len(found) - 15}개 더')
        print()
