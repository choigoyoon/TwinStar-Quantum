"""PnL 금액 계산 버그 추적"""
from pathlib import Path
import os
import sys

base = Path(__file__).parent
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 PnL 금액 계산 버그 추적")
print("=" * 70)

if not bot.exists():
    print("❌ unified_bot.py 없음")
    exit()

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

# 1) pnl_usd 계산 공식 찾기
print("\n[1] pnl_usd 계산 공식")
print("-" * 50)

for i, line in enumerate(lines, 1):
    if 'pnl_usd' in line.lower() and '=' in line:
        # 앞뒤 컨텍스트
        print(f"  L{i}: {line.strip()[:75]}")

# 2) 청산 함수에서 PnL 계산
print("\n[2] 청산 시 PnL 계산")
print("-" * 50)

funcs = ['_close_on_sl', '_execute_live_close', 'close_position', '_record_trade']
for func in funcs:
    in_func = False
    for i, line in enumerate(lines, 1):
        if f'def {func}' in line:
            in_func = True
            print(f"\n  === {func} ===")
            continue
        if in_func:
            if line.strip().startswith('def ') and func not in line:
                in_func = False
                break
            lower = line.lower()
            if 'pnl' in lower and ('=' in line or 'usd' in lower or 'amount' in lower):
                print(f"  L{i}: {line.strip()[:70]}")

# 3) Long/Short 방향 처리
print("\n[3] 방향별 PnL 계산")
print("-" * 50)

for i, line in enumerate(lines, 1):
    lower = line.lower()
    # pnl 계산에서 long/short 분기
    if 'pnl' in lower and ('long' in lower or 'short' in lower):
        print(f"  L{i}: {line.strip()[:75]}")
    # 또는 방향에 따른 부호
    if 'pnl' in lower and ('* -1' in line or '*-1' in line or '* 1' in line):
        print(f"  L{i}: {line.strip()[:75]}")

# 4) entry_price - exit_price 순서
print("\n[4] 가격 차이 계산 순서")
print("-" * 50)

for i, line in enumerate(lines, 1):
    if 'exit' in line.lower() and 'entry' in line.lower():
        if '-' in line:
            print(f"  L{i}: {line.strip()[:75]}")
    if 'close' in line.lower() and 'entry' in line.lower():
        if '-' in line:
            print(f"  L{i}: {line.strip()[:75]}")

# 5) pnl_pct vs pnl_usd 관계
print("\n[5] pnl_pct와 pnl_usd 관계")
print("-" * 50)

for i, line in enumerate(lines, 1):
    if 'pnl_pct' in line.lower() and 'pnl_usd' in line.lower():
        print(f"  L{i}: {line.strip()[:75]}")

# 6) 의심 패턴: pnl_pct를 usd로 잘못 사용
print("\n[6] 의심 패턴")
print("-" * 50)

for i, line in enumerate(lines, 1):
    # pnl_pct 값을 달러로 표시하는 버그
    if "'pnl_usd'" in line or '"pnl_usd"' in line:
        if 'pnl_pct' in line:
            print(f"  🔴 L{i}: {line.strip()[:70]}")
    # 또는 부호 반전
    if 'pnl' in line.lower() and '-pnl' in line.lower():
        print(f"  🔴 L{i}: {line.strip()[:70]}")

print("\n" + "=" * 70)
print("📋 예상 버그")
print("-" * 50)
print("""
[가능성 1] pnl_pct를 pnl_usd로 잘못 저장
  pnl_usd = pnl_pct  ← 버그! (0.86% → $0.86)

[가능성 2] 부호 반전
  pnl_usd = -pnl_usd  ← 버그!

[가능성 3] 계산 순서 오류
  Long: (entry - exit) 대신 (exit - entry) 사용해야 함

[정상 계산]
  pnl_usd = qty × (exit_price - entry_price)  # Long
  pnl_usd = qty × (entry_price - exit_price)  # Short
""")

print("\n결과 공유해줘")
