"""트레일링 업데이트 주기 확인"""
from pathlib import Path
import re

base = Path(r'C:\매매전략')
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 트레일링 업데이트 주기 확인")
print("=" * 70)

if not bot.exists():
    print("❌ unified_bot.py 없음")
    exit()

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

# 1) manage_position 호출 위치 및 컨텍스트
print("\n[1] manage_position / update_stop_loss 호출 위치")
print("-" * 50)

for i, line in enumerate(lines, 1):
    if 'manage_position' in line or 'update_stop_loss' in line:
        if 'def ' not in line:
            # 앞뒤 10줄 컨텍스트에서 트리거 찾기
            start = max(0, i-10)
            context = lines[start:i]
            
            trigger = "알 수 없음"
            for ctx in context:
                if 'while' in ctx.lower():
                    trigger = "while 루프"
                elif 'on_price' in ctx.lower() or 'price_update' in ctx.lower():
                    trigger = "가격 업데이트 이벤트"
                elif 'on_candle' in ctx.lower() or 'candle_close' in ctx.lower():
                    trigger = "봉마감 이벤트"
                elif 'sleep' in ctx.lower():
                    sleep_match = re.search(r'sleep\s*\(\s*(\d+\.?\d*)', ctx)
                    if sleep_match:
                        trigger = f"sleep({sleep_match.group(1)}초) 주기"
                elif 'timer' in ctx.lower() or 'interval' in ctx.lower():
                    trigger = "타이머/인터벌"
            
            print(f"  L{i}: {line.strip()[:60]}")
            print(f"       트리거: {trigger}")

# 2) 메인 루프 구조
print("\n[2] run() 메인 루프 구조")
print("-" * 50)

in_run = False
for i, line in enumerate(lines, 1):
    if 'def run(' in line:
        in_run = True
        print(f"  L{i}: {line.strip()}")
        continue
    if in_run:
        if line.strip().startswith('def ') and 'run' not in line:
            break
        lower = line.lower()
        # 핵심 구조만
        if 'while' in lower or 'sleep' in lower or 'asyncio' in lower:
            print(f"  L{i}: {line.strip()[:70]}")
        if 'manage_position' in line or 'update' in lower and 'sl' in lower:
            print(f"  L{i}: {line.strip()[:70]}")

# 3) sleep 주기 확인
print("\n[3] sleep 주기")
print("-" * 50)
sleeps = re.findall(r'sleep\s*\(\s*(\d+\.?\d*)\s*\)', code)
if sleeps:
    print(f"  발견된 sleep 값: {set(sleeps)}")
else:
    print("  sleep 없음")

# 4) 가격 이벤트 핸들러
print("\n[4] 가격 이벤트 핸들러")
print("-" * 50)
for i, line in enumerate(lines, 1):
    if 'def _on_price' in line or 'def on_price' in line or 'def _handle_price' in line:
        print(f"  L{i}: {line.strip()}")
        # 함수 내용 일부
        for j in range(i, min(i+15, len(lines))):
            if 'manage_position' in lines[j] or 'trailing' in lines[j].lower() or 'sl' in lines[j].lower():
                print(f"    L{j+1}: {lines[j].strip()[:65]}")

# 5) WebSocket 메시지 핸들러
print("\n[5] WebSocket 가격 수신")
print("-" * 50)
for i, line in enumerate(lines, 1):
    lower = line.lower()
    if 'on_message' in lower or 'ws_callback' in lower or 'price_callback' in lower:
        print(f"  L{i}: {line.strip()[:70]}")

print("\n" + "=" * 70)
print("📋 예상 시나리오")
print("-" * 50)
print("""
[가능한 업데이트 주기]

1. 실시간 틱: WebSocket 가격 올 때마다 (매 100ms~1초)
2. 봉마감: 1분/5분/15분 봉 닫힐 때마다
3. 주기적: while 루프 + sleep(N초)마다
4. 혼합: 봉마감 시 계산 + 실시간 SL 터치 체크

백테스트와 동일하려면?
→ 봉마감 기준이어야 함 (실시간이면 백테스트와 다름)
""")

print("\n결과 공유해줘")
