"""
백테스트 위젯 전체 영어 텍스트 검색
"""
import re

with open('GUI/backtest_widget.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('=== backtest_widget.py 영어 텍스트 검색 ===\n')

# 영어 단어 패턴 (2글자 이상)
english_pattern = re.compile(r'"([A-Za-z][A-Za-z\s\.:/%]+)"')

count = 0
for i, line in enumerate(lines):
    # UI 텍스트 관련 라인 검색
    if ('QLabel(' in line or 'QPushButton(' in line or 'setToolTip(' in line or 
        'setText(' in line or 'QGroupBox(' in line or 'addTab(' in line or
        'setPlaceholderText(' in line):
        
        # t() 사용 안 하는 경우만
        if 't(' not in line:
            matches = english_pattern.findall(line)
            if matches:
                for m in matches:
                    # PyQt 메서드명이나 스타일 제외
                    if not any(x in m for x in ['QPush', 'QLabel', 'color', 'background', 'font', 'border', 'padding']):
                        print(f'L{i+1}: "{m}" | {line.strip()[:50]}')
                        count += 1

print(f'\n총 {count}개 발견')
