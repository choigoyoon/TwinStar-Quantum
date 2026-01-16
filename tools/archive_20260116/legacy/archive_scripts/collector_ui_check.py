from pathlib import Path

f = Path(r'C:\매매전략\GUI\data_collector_widget.py')
lines = f.read_text(encoding='utf-8', errors='ignore').split('\n')

print('=== 수집기 UI 요소 확인 ===\n')

print('[1] 타임프레임 선택:')
for i, line in enumerate(lines):
    if 'timeframe' in line.lower() or 'interval' in line.lower():
        print(f'  L{i+1}: {line.strip()[:70]}')

print('\n[2] 날짜 선택:')
for i, line in enumerate(lines):
    if 'date' in line.lower() and ('edit' in line.lower() or 'select' in line.lower() or 'start' in line.lower() or 'end' in line.lower()):
        print(f'  L{i+1}: {line.strip()[:70]}')

print('\n[3] 수집 실행 함수:')
for i, line in enumerate(lines):
    if 'def ' in line and ('collect' in line.lower() or 'download' in line.lower() or 'fetch' in line.lower() or 'start' in line.lower()):
        print(f'  L{i+1}: {line.strip()[:70]}')
