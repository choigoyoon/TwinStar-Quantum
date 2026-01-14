"""백테스트 수수료 적용 횟수 확인"""
from pathlib import Path
import os
import sys

base = Path(__file__).parent
strategy = base / 'core' / 'strategy_core.py'

print("=" * 70)
print("🔍 백테스트 수수료 적용 횟수 확인")
print("=" * 70)

if not strategy.exists():
    print("❌ strategy_core.py 없음")
    exit()

code = strategy.read_text(encoding='utf-8')
lines = code.split('\n')

# 1) 수수료 변수 정의
print("\n[1] 수수료 변수 정의")
print("-" * 50)

for i, line in enumerate(lines, 1):
    if 'fee' in line.lower() and '=' in line:
        if '0.0' in line or 'fee' in line.lower():
            print(f"  L{i}: {line.strip()[:75]}")

# 2) 수수료 적용 위치 (진입/청산)
print("\n[2] 수수료 적용 위치")
print("-" * 50)

for i, line in enumerate(lines, 1):
    lower = line.lower()
    if ('fee' in lower or 'slippage' in lower) and ('*' in line or '-' in line):
        # 앞뒤 컨텍스트
        context_start = max(0, i-3)
        context_end = min(len(lines), i+2)
        
        print(f"\n  L{i}: {line.strip()[:70]}")
        for j in range(context_start, context_end):
            if j != i-1:
                ctx = lines[j].strip()[:60]
                if ctx:
                    print(f"    L{j+1}: {ctx}")

# 3) PnL 계산에서 수수료 차감
print("\n[3] PnL 계산 시 수수료 차감")
print("-" * 50)

in_backtest = False
for i, line in enumerate(lines, 1):
    if 'def run_backtest' in line:
        in_backtest = True
    if in_backtest:
        if line.strip().startswith('def ') and 'backtest' not in line.lower():
            in_backtest = False
            break
        lower = line.lower()
        if 'pnl' in lower and ('fee' in lower or 'slippage' in lower):
            print(f"  L{i}: {line.strip()[:70]}")
        if ('fee' in lower or 'slippage' in lower) and ('*' in line or '2' in line):
            print(f"  L{i}: {line.strip()[:70]}")

# 4) 수수료 * 2 패턴 (왕복)
print("\n[4] 왕복 수수료 패턴 (fee * 2)")
print("-" * 50)

found_double = False
for i, line in enumerate(lines, 1):
    lower = line.lower()
    if 'fee' in lower or 'slippage' in lower:
        if '* 2' in line or '*2' in line or '2 *' in line or '2*' in line:
            print(f"  ✅ L{i}: {line.strip()[:70]} ← 왕복!")
            found_double = True

if not found_double:
    print("  ❓ fee/slippage * 2 패턴 없음 → 편도 적용 가능성")

# 5) 실제 계산식 추출
print("\n[5] 실제 PnL 계산식")
print("-" * 50)

for i, line in enumerate(lines, 1):
    lower = line.lower()
    if 'pnl' in lower and '=' in line:
        if 'fee' in lower or 'slippage' in lower or 'entry' in lower or 'exit' in lower:
            print(f"  L{i}: {line.strip()[:75]}")

print("\n" + "=" * 70)
print("📋 수수료 정리")
print("-" * 50)
print("""
[예상 시나리오]

A) 편도 적용 (fee = 0.06%):
   진입 시: -0.06%
   청산 시: -0.06%
   총: -0.12%

B) 왕복 적용 (fee = 0.06%):
   1회만 차감: -0.06% (진입+청산 합산)

[바이빗 실제]
   Taker 왕복: 0.055% × 2 = 0.11%

[확인 필요]
   백테스트가 0.06%를 몇 번 적용하는지
""")

print("\n결과 공유해줘")
