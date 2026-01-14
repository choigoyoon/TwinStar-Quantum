
from pathlib import Path

base = Path(__file__).parent

# binance_exchange.py 확인
binance_file = base / 'exchanges' / 'binance_exchange.py'

if binance_file.exists():
    code = binance_file.read_text(encoding='utf-8', errors='ignore')
    print("=" * 60)
    print("binance_exchange.py 현재 구조")
    print("=" * 60)
    
    lines = code.split('\n')
    
    # 클래스와 메서드 목록
    print("\n[메서드 목록]")
    for i, line in enumerate(lines):
        if 'def ' in line and '(' in line:
            print(f"  L{i+1}: {line.strip()[:60]}")
    
    # WS 관련 코드
    print("\n[WS 관련 코드]")
    ws_related = []
    for i, line in enumerate(lines):
        if any(k in line.lower() for k in ['websocket', 'ws_', 'stream', 'subscribe']):
            ws_related.append(f"  L{i+1}: {line.strip()[:60]}")
    
    if ws_related:
        for w in ws_related[:10]:
            print(w)
    else:
        print("  ❌ WS 관련 코드 없음")
    
    # import 확인
    print("\n[imports]")
    for i, line in enumerate(lines[:30]):
        if 'import' in line:
            print(f"  {line.strip()}")

else:
    print("❌ binance_exchange.py 파일 없음")

# ws_handler.py 확인 (Bybit용)
print("\n" + "=" * 60)
print("ws_handler.py 구조 (참고용)")
print("=" * 60)

ws_handler = base / 'exchanges' / 'ws_handler.py'
if ws_handler.exists():
    try:
        ws_code = ws_handler.read_text(encoding='utf-8')
        ws_lines = ws_code.split('\n')
        
        print("\n[핵심 메서드]")
        for i, line in enumerate(ws_lines):
            if 'def ' in line:
                print(f"  L{i+1}: {line.strip()[:50]}")
        
        print("\n[WS 연결 로직]")
        for i, line in enumerate(ws_lines):
            if 'connect' in line.lower() or 'subscribe' in line.lower():
                print(f"  L{i+1}: {line.strip()[:60]}")
    except Exception as e:
        print(f"Error reading ws_handler.py: {e}")
