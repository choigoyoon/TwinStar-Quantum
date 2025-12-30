"""진입 타이밍 로직 체크: 봉마감 vs 실시간"""
from pathlib import Path

base = Path(r'C:\매매전략')
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 진입 타이밍 로직 체크")
print("=" * 70)

if not bot.exists():
    print("❌ unified_bot.py 없음")
    exit()

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

# 1) 봉마감 감지 로직
print("\n[1] 봉마감 감지 로직")
print("-" * 50)
candle_patterns = ['candle_close', 'on_candle', 'is_closed', 'kline_close', 
                   'bar_close', 'new_candle', 'candle_confirmed']
for i, line in enumerate(lines, 1):
    lower = line.lower()
    for p in candle_patterns:
        if p in lower:
            print(f"  L{i}: {line.strip()[:80]}")
            break

# 2) 진입 트리거 위치
print("\n[2] 진입 트리거 (execute_entry 호출 위치)")
print("-" * 50)
for i, line in enumerate(lines, 1):
    if 'execute_entry' in line and 'def ' not in line:
        # 앞뒤 컨텍스트
        start = max(0, i-3)
        print(f"\n  --- L{i} 주변 ---")
        for j in range(start, min(i+2, len(lines))):
            marker = ">>>" if j == i-1 else "   "
            print(f"  {marker} L{j+1}: {lines[j].strip()[:70]}")

# 3) 시그널 감지 → 진입 흐름
print("\n[3] detect_signal → execute_entry 흐름")
print("-" * 50)
for i, line in enumerate(lines, 1):
    if 'detect_signal' in line and 'def ' not in line:
        print(f"  L{i}: {line.strip()[:80]}")

# 4) 실시간 가격 진입 여부
print("\n[4] 실시간 가격으로 바로 진입하는지")
print("-" * 50)
for i, line in enumerate(lines, 1):
    lower = line.lower()
    if 'current_price' in lower and 'entry' in lower:
        print(f"  L{i}: {line.strip()[:80]}")
    if 'execute_entry' in line and 'price' in line:
        print(f"  L{i}: {line.strip()[:80]}")

# 5) 봉마감 대기 로직 유무
print("\n[5] 봉마감 대기 로직 존재 여부")
print("-" * 50)
wait_patterns = ['wait.*candle', 'candle.*wait', 'wait.*close', 
                 'pending.*signal', 'queue.*signal', 'validity']
found_wait = False
for i, line in enumerate(lines, 1):
    lower = line.lower()
    for p in wait_patterns:
        if p.replace('.*', '') in lower or (p.split('.*')[0] in lower and p.split('.*')[1] in lower):
            print(f"  L{i}: {line.strip()[:80]}")
            found_wait = True
            break

if not found_wait:
    print("  ⚠️ 봉마감 대기 로직 없음 - 실시간 진입 가능성")

print("\n" + "=" * 70)
print("결과 공유해줘 - 봉마감 없이 진입하는 원인 찾자")
