from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략\exchanges')

exchanges = {
    'bybit_exchange.py': 'positionIdx',
    'binance_exchange.py': 'positionSide',
    'bitget_exchange.py': 'holdSide',
    'okx_exchange.py': 'posSide',
    'bingx_exchange.py': 'positionSide',
}

print('선물 거래소 포지션 조회 Hedge Mode 지원 확인:')
print('=' * 60)

for fname, hedge_key in exchanges.items():
    path = base / fname
    if not path.exists():
        print(f'X {fname}: 파일 없음')
        continue
    
    code = path.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    has_func = 'get_position' in code or 'get_open_position' in code
    has_hedge = hedge_key.lower() in code.lower()
    has_both = 'long' in code.lower() and 'short' in code.lower()
    
    status = []
    if has_func:
        status.append('포지션조회O')
    else:
        status.append('포지션조회X')
    
    if has_hedge:
        status.append(f'{hedge_key}O')
    else:
        status.append(f'{hedge_key}X')
    
    if has_both:
        status.append('Long/ShortO')
    else:
        status.append('Long/ShortX')
    
    print(f'{fname}: {" | ".join(status)}')
    
    for i, line in enumerate(lines):
        if 'def get_position' in line or 'def get_open_position' in line:
            print(f'  L{i+1}: {line.strip()[:50]}')
