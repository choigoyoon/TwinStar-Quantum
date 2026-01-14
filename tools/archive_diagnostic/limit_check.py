from pathlib import Path

base = Path(__file__).parent
target = base / 'GUI' / 'data_collector_widget.py'

print('=== 데이터 수집기 limit 분석 ===\n')

if target.exists():
    code = target.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    # limit 관련 라인
    print('[1] limit 설정 라인:')
    for i, line in enumerate(lines):
        if 'limit' in line.lower() and '=' in line:
            print(f'  L{i+1}: {line.strip()[:80]}')
    
    # fetch_ohlcv 호출
    print('\n[2] fetch_ohlcv 호출:')
    for i, line in enumerate(lines):
        if 'fetch_ohlcv' in line:
            print(f'  L{i+1}: {line.strip()[:80]}')
    
    # 페이지네이션 (while/for + since)
    print('\n[3] 페이지네이션 로직:')
    has_pagination = False
    for i, line in enumerate(lines):
        if ('while' in line or 'for' in line) and ('since' in lines[min(i+5, len(lines)-1)] or 'since' in line):
            print(f'  L{i+1}: {line.strip()[:80]}')
            has_pagination = True
    if not has_pagination:
        print('  ⚠️ 페이지네이션 로직 없음!')

# 거래소 어댑터도 확인
print('\n[4] 거래소별 limit 확인:')
for ex in ['bybit', 'binance', 'okx']:
    f = base / 'exchanges' / f'{ex}_exchange.py'
    if f.exists():
        code = f.read_text(encoding='utf-8', errors='ignore')
        for i, line in enumerate(code.split('\n')):
            if 'limit' in line.lower() and ('1000' in line or '200' in line or '500' in line):
                print(f'  {ex} L{i+1}: {line.strip()[:70]}')
