from pathlib import Path
import re
import sys
import io

# Ensure plain output for terminal readability
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

base = Path(r'C:\매매전략\exchanges')

print("=" * 70)
print("거래소별 실제 함수 존재 여부 (코드 직접 확인)")
print("=" * 70)

exchanges = ['bybit', 'binance', 'okx', 'bitget', 'bingx', 'upbit', 'bithumb']

for ex in exchanges:
    f = base / f'{ex}_exchange.py'
    if not f.exists():
        print(f"\n[!] {ex}_exchange.py 파일 없음")
        continue
    
    code = f.read_text(encoding='utf-8', errors='ignore')
    
    print(f"\n[{ex.upper()}]")
    
    # 1. 포지션 조회
    pos_match = re.search(r'def\s+(get_position[s]?|fetch_position[s]?)\s*\(', code)
    if pos_match:
        func_name = pos_match.group(1)
        print(f"  O 포지션: {func_name}()")
        
        # 실제 구현 내용 확인 (빈 함수인지)
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if f'def {func_name}' in line:
                # 다음 10줄까지 본문 확인 (주석/빈줄 제외)
                body_lines = []
                for j in range(i+1, min(i+15, len(lines))):
                    l = lines[j].strip()
                    if l and not l.startswith('#') and not l.startswith('"""') and not l.startswith("'''"):
                        body_lines.append(l)
                
                if body_lines:
                    first_real_line = body_lines[0]
                    if first_real_line == 'pass' or 'raise NotImplementedError' in first_real_line:
                        print(f"    [!] {func_name}은 빈 함수 (pass/NotImplementedError)")
                break
    else:
        print(f"  X 포지션: 함수 없음")
    
    # 2. 거래 내역
    hist_match = re.search(r'def\s+(get_trade_history|fetch_my_trades|get_order_history|fetch_orders)\s*\(', code)
    if hist_match:
        print(f"  O 거래내역: {hist_match.group(1)}()")
    else:
        if 'fetch_my_trades' in code:
            print(f"  [!] 거래내역: ccxt.fetch_my_trades 직접 호출")
        elif 'fetch_orders' in code:
            print(f"  [!] 거래내역: ccxt.fetch_orders 직접 호출")
        else:
            print(f"  X 거래내역: 없음")
    
    # 3. 잔고 조회
    bal_match = re.search(r'def\s+(get_balance|fetch_balance)\s*\(', code)
    if bal_match:
        print(f"  O 잔고: {bal_match.group(1)}()")
    else:
        print(f"  X 잔고: 함수 없음")

print("\n" + "=" * 70)
print("검증 완료")
print("=" * 70)
