from pathlib import Path
import re

base = Path(r'C:\매매전략')

print('=' * 70)
print('💱 KRW / USDT 통화 처리 전수 스캔')
print('=' * 70)

results = {
    'krw_usage': [],
    'usdt_usage': [],
    'get_balance': [],
    'quote_currency': [],
    'hardcoded_currency': [],
}

for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        fname = f.relative_to(base).as_posix()
        
        for i, line in enumerate(lines):
            ln = i + 1
            
            # KRW 사용
            if 'KRW' in line and '#' not in line.split('KRW')[0]:
                results['krw_usage'].append((fname, ln, line.strip()[:60]))
            
            # USDT 사용
            if 'USDT' in line and '#' not in line.split('USDT')[0]:
                results['usdt_usage'].append((fname, ln, line.strip()[:60]))
            
            # get_balance 호출
            if 'get_balance' in line or 'fetch_balance' in line:
                results['get_balance'].append((fname, ln, line.strip()[:60]))
            
            # quote_currency / base_currency
            if 'quote' in line.lower() and 'currency' in line.lower():
                results['quote_currency'].append((fname, ln, line.strip()[:60]))
            
            # 하드코딩된 통화
            if re.search(r'["\']USDT["\']|["\']KRW["\']|["\']USD["\']', line):
                results['hardcoded_currency'].append((fname, ln, line.strip()[:60]))
                
    except Exception:

                
        pass

# 결과 출력
print(f'\n📊 [1] KRW 사용: {len(results["krw_usage"])}건')
for fname, ln, code in results['krw_usage'][:10]:
    print(f'   {fname} L{ln}: {code}')
if len(results['krw_usage']) > 10:
    print(f'   ... 외 {len(results["krw_usage"])-10}건')

print(f'\n📊 [2] USDT 사용: {len(results["usdt_usage"])}건')
for fname, ln, code in results['usdt_usage'][:10]:
    print(f'   {fname} L{ln}: {code}')
if len(results['usdt_usage']) > 10:
    print(f'   ... 외 {len(results["usdt_usage"])-10}건')

print(f'\n📊 [3] get_balance 호출: {len(results["get_balance"])}건')
for fname, ln, code in results['get_balance'][:10]:
    print(f'   {fname} L{ln}: {code}')

print(f'\n📊 [4] 하드코딩 통화: {len(results["hardcoded_currency"])}건')
for fname, ln, code in results['hardcoded_currency'][:10]:
    print(f'   {fname} L{ln}: {code}')

print('\n' + '=' * 70)

# 거래소별 통화 설정 확인
print('\n🏦 [5] 거래소별 통화 설정')
exchanges = ['upbit', 'bithumb', 'bybit', 'binance', 'okx', 'bitget', 'bingx']

for ex in exchanges:
    ex_file = base / 'exchanges' / f'{ex}_exchange.py'
    if ex_file.exists():
        code = ex_file.read_text(encoding='utf-8', errors='ignore')
        has_krw = 'KRW' in code
        has_usdt = 'USDT' in code
        has_quote = 'quote' in code.lower()
        print(f'   {ex}: KRW={has_krw} USDT={has_usdt} quote설정={has_quote}')
    else:
        print(f'   {ex}: ❌ 파일 없음')

print('=' * 70)
