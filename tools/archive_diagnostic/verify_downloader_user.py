import os
import sys
from pathlib import Path

path = r'C:\매매전략\utils\data_downloader.py'

print('=== [1] 파일 및 함수 체크 ===')
if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f'파일 크기: {len(content)} bytes')
    print(f'총 라인: {len(content.split(chr(10)))}줄')
    
    print('\n=== 함수 목록 ===')
    for i, line in enumerate(content.split('\n')):
        if line.strip().startswith('def '):
            print(f'L{i+1}: {line.strip()[:60]}')
else:
    print('❌ 파일 없음')
    sys.exit(1)

print('\n=== [2] TODO 체크 ===')
has_shutil = 'import shutil' in content
print(f'[{"✅" if has_shutil else "❌"}] TODO 1: import shutil')

has_filter = 'def get_filtered_symbols' in content
print(f'[{"✅" if has_filter else "❌"}] TODO 2: get_filtered_symbols()')

has_intersection = '&' in content or 'intersection' in content
print(f'[{"✅" if has_intersection else "❌"}] TODO 3: 교집합 로직')

has_copy = 'shutil.copy' in content
print(f'[{"✅" if has_copy else "❌"}] TODO 4: shutil.copy 복사')

has_bithumb = "exchange_name == 'bithumb'" in content or 'bithumb' in content.lower()
print(f'[{"✅" if has_bithumb else "❌"}] TODO 5: 빗썸 분기 처리')

print('\n=== [3] 문법 검사 ===')
try:
    compile(content, path, 'exec')
    print('✅ 문법 검사 통과')
except SyntaxError as e:
    print(f'❌ 문법 오류: {e}')

print('\n=== [4] 실제 동작 테스트 (Bithumb Filtering) ===')
try:
    sys.path.append(str(Path.cwd()))
    from utils.data_downloader import get_filtered_symbols
    symbols = get_filtered_symbols('bithumb')
    print(f'Bithumb Filtered Symbols (Intersection): {len(symbols)} coins')
    print(f'Sample (Top 10): {symbols[:10]}')
except Exception as e:
    print(f'❌ 동작 오류: {e}')
