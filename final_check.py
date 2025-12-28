import os

# 최종 영어 텍스트 검색 - 수집 및 백테스트 탭
print('=== 최종 영어 텍스트 검색 ===\n')

files = ['GUI/data_collector_widget.py', 'GUI/backtest_widget.py', 'GUI/data_download_widget.py']

for fpath in files:
    if not os.path.exists(fpath):
        continue
    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    print(f'--- {os.path.basename(fpath)} ---')
    found = 0
    for i, line in enumerate(lines):
        # UI 텍스트 패턴 (QLabel, QPushButton, setToolTip, setText, setWindowTitle 등)
        if ('QLabel(' in line or 'QPushButton(' in line or 'setToolTip(' in line or 
            'setText(' in line or 'QGroupBox(' in line or 'setWindowTitle(' in line):
            if 't(' not in line:
                # 영어 단어 포함 확인
                import re
                english = re.findall(r'"([A-Za-z][A-Za-z\s]+)"', line)
                if english:
                    print(f'  L{i+1}: {line.strip()[:60]}')
                    found += 1
                    if found >= 10:
                        print('  ... (더 있음)')
                        break
    if found == 0:
        print('  ✅ 영어 텍스트 없음')
    print()
