
from pathlib import Path

base = Path(__file__).parent

print("=" * 60)
print("거래소별 WS 구현 상태 상세 분석")
print("=" * 60)

exchanges_dir = base / 'exchanges'

for ex_file in sorted(exchanges_dir.glob('*_exchange.py')):
    name = ex_file.stem.replace('_exchange', '')
    code = ex_file.read_text(encoding='utf-8', errors='ignore')
    
    print(f"\n{'='*40}")
    print(f"[{name.upper()}]")
    print(f"{'='*40}")
    
    # 1. start_websocket 메서드
    if 'def start_websocket' in code:
        print("  ✅ start_websocket 메서드 존재")
        
        # 실제 구현 내용 확인
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if 'def start_websocket' in line:
                # 다음 20줄 확인
                impl_lines = lines[i:i+20]
                has_ws_connect = any('websocket' in l.lower() or 'ws.' in l.lower() or 'connect' in l.lower() for l in impl_lines)
                has_pass = any(l.strip() == 'pass' for l in impl_lines[:5])
                has_return_false = any('return False' in l for l in impl_lines[:10])
                
                if has_pass or has_return_false:
                    print("  ⚠️ 미구현 (pass/return False)")
                elif has_ws_connect:
                    print("  ✅ 실제 WS 연결 구현")
                break
    else:
        print("  ❌ start_websocket 없음")
    
    # 2. WS 관련 import
    if 'import websocket' in code or 'from websocket' in code:
        print("  ✅ websocket 라이브러리 import")
    elif 'ws_handler' in code:
        print("  ✅ ws_handler 사용")
    else:
        print("  ❌ WS 라이브러리 없음")
    
    # 3. 봉 마감 콜백
    if 'on_candle_close' in code or 'on_kline' in code:
        print("  ✅ 봉 마감 콜백")
    else:
        print("  ❌ 봉 마감 콜백 없음")
    
    # 4. REST fallback
    if 'get_klines' in code:
        print("  ✅ get_klines (REST)")

print("\n" + "=" * 60)
print("결론")
print("=" * 60)
print("""
[현재 상태]
- Bybit: WS 완전 지원 ✅
- 나머지: REST 폴링만 지원 (WS 미구현)

[문제점]
- WS 없으면 봉 마감 실시간 감지 불가
- REST 폴링은 1초 단위 → 지연 발생
- 진입 타이밍 늦어짐 → 슬리피지 증가

[해결 필요]
1. Binance WS 구현 (가장 중요)
2. Upbit/Bithumb WS 구현
3. 또는 REST 폴링 최적화
""")
