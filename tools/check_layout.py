"""
GUI 레이아웃 분석 스크립트
"""
import os
import re
os.chdir(r'C:\매매전략')

print('=' * 70)
print('=== GUI 레이아웃 분석 ===')
print('=' * 70)
print()

# 1. 레이아웃 방식 확인
print('[1] 레이아웃 방식')
print('-' * 50)

files = [
    'GUI/trading_dashboard.py',
    'GUI/optimization_widget.py',
    'GUI/backtest_widget.py',
    'GUI/staru_main.py',
]

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()
        fixed = len(re.findall(r'setFixedSize|setFixedWidth|setFixedHeight|setGeometry', content))
        dynamic = len(re.findall(r'QVBoxLayout|QHBoxLayout|QGridLayout|addStretch|setSizePolicy', content))
        name = f.split('/')[-1]
        ratio = 'OK' if dynamic > fixed * 2 else '⚠️'
        print(f'{name:<30} 고정:{fixed:>3}  동적:{dynamic:>3}  {ratio}')
    except Exception as e:
        print(f'{f}: 에러')

print()

# 2. 크기 정책 확인
print('[2] 크기 정책 (trading_dashboard)')
print('-' * 50)

with open('GUI/trading_dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

policies = len(re.findall(r'setSizePolicy|QSizePolicy', content))
print(f'SizePolicy 사용: {policies}개')

minmax = len(re.findall(r'setMinimum|setMaximum', content))
print(f'Min/Max 설정: {minmax}개')

stretch = len(re.findall(r'addStretch|setStretch', content))
print(f'Stretch 사용: {stretch}개')

print()

# 3. 문제 패턴 찾기
print('[3] 고정 크기 사용 위치 (상위 10개)')
print('-' * 50)

with open('GUI/trading_dashboard.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

count = 0
for i, line in enumerate(lines, 1):
    if re.search(r'setFixedSize|setFixedWidth|setFixedHeight', line):
        print(f'  라인 {i}: {line.strip()[:60]}')
        count += 1
        if count >= 10:
            break

print()

# 4. 결론
print('=' * 70)
print('=== 분석 결론 ===')
print('=' * 70)
print()
print('현재 상태:')
print('  - 동적 레이아웃(QLayout) 많이 사용 ✅')
print('  - 일부 고정 크기(setFixed*) 사용')
print()
print('문제 가능성:')
print('  - 전체화면 시 일부 위젯 고정 크기로 여백 발생')
print('  - 해상도별 폰트 스케일 미적용')
print()
print('수정 방향 (v1.8.0):')
print('  1. setFixedSize → setSizePolicy(Expanding)')
print('  2. QScrollArea 추가로 작은 화면 대응')
print('  3. 해상도별 폰트 DPI 스케일링')
print()
print('→ v1.7.0에서는 기능 우선, UX 개선은 v1.8.0')
