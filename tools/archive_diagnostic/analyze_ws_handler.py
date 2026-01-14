
from pathlib import Path

base = Path(__file__).parent
ws_handler = base / 'exchanges' / 'ws_handler.py'

print("=" * 60)
print("Phase 1: ws_handler.py 현재 구조 분석")
print("=" * 60)

code = ws_handler.read_text(encoding='utf-8')
lines = code.split('\n')

# 1. 현재 지원 거래소
print("\n[1] 현재 지원 거래소 (WS 엔드포인트)")
for i, line in enumerate(lines):
    if 'wss://' in line or 'WSS_' in line or 'ws_url' in line.lower():
        print(f"  L{i+1}: {line.strip()[:70]}")

# 2. 메시지 파싱 로직
print("\n[2] 메시지 파싱 로직")
for i, line in enumerate(lines):
    if 'def _parse' in line or 'def parse' in line:
        print(f"  L{i+1}: {line.strip()}")

# 3. 거래소별 분기
print("\n[3] 거래소별 분기 처리")
for i, line in enumerate(lines):
    if 'bybit' in line.lower() or 'binance' in line.lower():
        if 'if ' in line or 'elif ' in line:
            print(f"  L{i+1}: {line.strip()[:60]}")

# 4. 클래스 구조
print("\n[4] 클래스/메서드 구조")
for i, line in enumerate(lines):
    if line.strip().startswith('class ') or line.strip().startswith('def '):
        indent = len(line) - len(line.lstrip())
        if indent <= 4:
            print(f"  L{i+1}: {line.strip()[:50]}")

# 5. 필요한 거래소 WS 정보
print("\n" + "=" * 60)
print("추가 필요한 거래소 WS 엔드포인트")
print("=" * 60)

ws_endpoints = {
    'binance': {
        'futures': 'wss://fstream.binance.com/ws',
        'spot': 'wss://stream.binance.com:9443/ws',
        'kline': '<symbol>@kline_<interval>',
        'example': 'btcusdt@kline_15m'
    },
    'upbit': {
        'url': 'wss://api.upbit.com/websocket/v1',
        'format': 'JSON ticket + type',
        'note': '국내 거래소, 인증 필요 없음'
    },
    'bithumb': {
        'url': 'wss://pubwss.bithumb.com/pub/ws',
        'format': 'JSON subscribe',
        'note': '국내 거래소'
    },
    'okx': {
        'url': 'wss://ws.okx.com:8443/ws/v5/public',
        'channel': 'candle<interval>',
        'example': 'candle15m'
    },
    'bitget': {
        'url': 'wss://ws.bitget.com/mix/v1/stream',
        'channel': 'candle<interval>',
    },
    'bingx': {
        'url': 'wss://open-api-swap.bingx.com/swap-market',
        'channel': '<symbol>@kline_<interval>',
    }
}

for ex, info in ws_endpoints.items():
    print(f"\n[{ex.upper()}]")
    for k, v in info.items():
        print(f"  {k}: {v}")

print("\n" + "=" * 60)
print("ws_handler.py 확장 코드 생성 준비됨")
print("=" * 60)
