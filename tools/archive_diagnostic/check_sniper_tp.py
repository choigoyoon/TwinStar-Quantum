"""multi_sniper.py TP 로직 확인 및 수정 가이드"""
from pathlib import Path

base = Path(__file__).parent
sniper = base / 'core' / 'multi_sniper.py'

print("=" * 70)
print("🔍 multi_sniper.py TP 로직 확인")
print("=" * 70)

if not sniper.exists():
    print("❌ multi_sniper.py 없음")
    exit()

code = sniper.read_text(encoding='utf-8')
lines = code.split('\n')

# 1) TP 관련 라인 찾기
print("\n[1] TP 계산 위치")
print("-" * 50)
tp_lines = []
for i, line in enumerate(lines, 1):
    lower = line.lower()
    if 'tp' in lower or 'take_profit' in lower or '1.02' in line:
        if '=' in line or 'price' in lower:
            tp_lines.append((i, line.strip()))

for ln, txt in tp_lines[:15]:
    print(f"  L{ln}: {txt[:70]}")

# 2) L850 주변 컨텍스트
print("\n[2] L850 주변 코드")
print("-" * 50)
start = max(0, 840)
end = min(len(lines), 870)
for i in range(start, end):
    marker = ">>>" if i == 849 else "   "
    print(f"{marker} L{i+1}: {lines[i].rstrip()[:70]}")

# 3) strategy_core 연결 확인
print("\n[3] strategy_core 연결 상태")
print("-" * 50)
connections = []
for i, line in enumerate(lines, 1):
    if 'strategy' in line.lower() or 'alphax7' in line.lower() or 'core' in line.lower():
        if 'import' in line.lower() or 'self.' in line:
            connections.append(f"  L{i}: {line.strip()[:65]}")

if connections:
    for c in connections[:10]:
        print(c)
else:
    print("  ❌ strategy_core 연결 없음")

# 4) 수정 가이드
print("\n" + "=" * 70)
print("📋 수정 가이드")
print("-" * 50)
print("""
[현재] 하드코딩 TP
  tp_price = entry_price * 1.02  # 2% 고정

[수정] strategy_core 방식으로 통일
  # 옵션 1: ATR 기반 TP
  tp_price = entry_price + (atr * atr_mult * 2)
  
  # 옵션 2: strategy_core 호출
  tp_price = self.strategy.calculate_tp(entry_price, atr, direction)
  
  # 옵션 3: Trailing Stop만 사용 (TP 없음)
  tp_price = None  # Trailing이 익절 담당
""")

print("\n어떤 방식으로 수정할까?")
print("  1) ATR 기반 TP")
print("  2) strategy_core 호출")
print("  3) TP 제거 (Trailing만)")
print("\n결과 공유해줘")
