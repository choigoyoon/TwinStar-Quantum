"""트레일링 업데이트 타이밍 확인"""
from pathlib import Path

base = Path(__file__).parent
strategy = base / 'core' / 'strategy_core.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 트레일링 업데이트 타이밍 확인")
print("=" * 70)

# 1) strategy_core - manage_position_realtime 호출 조건
print("\n[1] manage_position_realtime 함수 구조")
print("-" * 50)
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    in_func = False
    for i, line in enumerate(lines, 1):
        if 'def manage_position_realtime' in line:
            in_func = True
            print(f"  L{i}: {line.strip()}")
            continue
        if in_func:
            if line.strip().startswith('def ') and 'manage_position' not in line:
                break
            # 핵심 로직만
            if 'trail' in line.lower() or 'sl' in line.lower() or 'update' in line.lower():
                print(f"  L{i}: {line.strip()[:70]}")

# 2) unified_bot - 언제 manage_position 호출하는지
print("\n[2] unified_bot에서 호출 타이밍")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        if 'manage_position' in line and 'def ' not in line:
            # 앞뒤 컨텍스트
            start = max(0, i-3)
            print(f"\n  === L{i} 호출 컨텍스트 ===")
            for j in range(start, min(i+2, len(lines))):
                marker = ">>>" if j == i-1 else "   "
                print(f"  {marker} L{j+1}: {lines[j].strip()[:65]}")

# 3) 가격 업데이트 이벤트
print("\n[3] 가격 업데이트 이벤트")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        if 'on_price' in lower or '_on_price' in lower or 'price_update' in lower:
            print(f"  L{i}: {line.strip()[:70]}")
        if 'on_candle' in lower or 'candle_close' in lower:
            print(f"  L{i}: {line.strip()[:70]}")

# 4) 주기적 체크 (Timer/Sleep)
print("\n[4] 주기적 체크 로직")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        if 'sleep' in line.lower() or 'timer' in line.lower() or 'interval' in line.lower():
            if 'import' not in line.lower():
                print(f"  L{i}: {line.strip()[:70]}")

print("\n" + "=" * 70)
print("📋 확인 포인트")
print("-" * 50)
print("""
[질문]
1. 트레일링은 실시간 틱마다? 봉마감마다?
2. 백테스트와 동일한 타이밍인가?
3. 거래소 SL 주문도 같이 업데이트되나?
""")
print("\n결과 공유해줘")
