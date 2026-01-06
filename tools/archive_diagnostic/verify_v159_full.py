"""v1.5.9 상태 복구 + 트레일링 이어가기 검증"""
from pathlib import Path
import json
import os
import sys

base = Path(r'C:\매매전략')
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 v1.5.9 상태 복구 검증")
print("=" * 70)

if not bot.exists():
    print("❌ unified_bot.py 없음")
    exit()

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

# 1) load_state에서 extreme_price 복구
print("\n[1] load_state - extreme_price 복구")
print("-" * 50)

in_func = False
for i, line in enumerate(lines, 1):
    if 'def load_state' in line:
        in_func = True
        print(f"  L{i}: {line.strip()}")
        continue
    if in_func:
        if line.strip().startswith('def ') and 'load_state' not in line:
            in_func = False
            break
        if 'extreme' in line.lower() or 'position' in line.lower():
            print(f"  L{i}: {line.strip()[:70]}")

# 2) save_state에서 extreme_price 저장
print("\n[2] save_state - extreme_price 저장")
print("-" * 50)

in_func = False
for i, line in enumerate(lines, 1):
    if 'def save_state' in line:
        in_func = True
        print(f"  L{i}: {line.strip()}")
        continue
    if in_func:
        if line.strip().startswith('def ') and 'save_state' not in line:
            in_func = False
            break
        if 'extreme' in line.lower():
            print(f"  L{i}: {line.strip()[:70]}")

# 3) manage_position에서 extreme_price 사용
print("\n[3] manage_position - extreme_price 초기화")
print("-" * 50)

in_func = False
for i, line in enumerate(lines, 1):
    if 'def manage_position' in line or 'def _manage_position' in line:
        in_func = True
        print(f"  L{i}: {line.strip()}")
        continue
    if in_func:
        if line.strip().startswith('def ') and 'manage_position' not in line:
            in_func = False
            break
        if 'extreme' in line.lower():
            print(f"  L{i}: {line.strip()[:70]}")

# 4) sync_position Adoptive 로직
print("\n[4] sync_position - Adoptive 로직")
print("-" * 50)

in_func = False
for i, line in enumerate(lines, 1):
    if 'def sync_position' in line:
        in_func = True
        print(f"  L{i}: {line.strip()}")
        continue
    if in_func:
        if line.strip().startswith('def ') and 'sync_position' not in line:
            in_func = False
            break
        lower = line.lower()
        if 'adopt' in lower or 'external' in lower or 'bt_state' in lower or 'matching' in lower:
            print(f"  L{i}: {line.strip()[:70]}")

# 5) _run_backtest_to_now 포지션 보존
print("\n[5] _run_backtest_to_now - 기존 포지션 보존")
print("-" * 50)

in_func = False
for i, line in enumerate(lines, 1):
    if 'def _run_backtest_to_now' in line:
        in_func = True
        print(f"  L{i}: {line.strip()}")
        continue
    if in_func:
        if line.strip().startswith('def ') and 'backtest_to_now' not in line:
            in_func = False
            break
        if 'self.position' in line or 'preserve' in line.lower() or 'existing' in line.lower() or 'over backtest' in line.lower():
            print(f"  L{i}: {line.strip()[:70]}")

# 6) 저장되는 상태 데이터 구조
print("\n[6] 저장되는 상태 데이터")
print("-" * 50)

state_keys = ['position', 'entry_price', 'sl_price', 'extreme_price', 
              'trailing_active', 'current_sl', 'order_id']

for key in state_keys:
    found = False
    for i, line in enumerate(lines, 1):
        if f"'{key}'" in line or f'"{key}"' in line:
            # Check context
            context = lines[max(0,i-50):i]
            if any('save_state' in ctx for ctx in context):
                if 'state[' in line or 'data[' in line or key == 'extreme_price':
                    print(f"  ✅ {key}: L{i} - {line.strip()[:60]}")
                    found = True
                    break
    if not found:
        # 다시 검색 (더 넓게)
        for i, line in enumerate(lines, 1):
            if key in line and ('state' in line.lower() or 'save' in line.lower()):
                 if 'save_state' in lines[max(0, i-50):i][-1] if lines[max(0, i-50):i] else True: # heuristic
                    print(f"  ✅ {key}: L{i} - {line.strip()[:60]}")
                    found = True
                    break
    if not found:
        print(f"  ❓ {key}: 확인 필요")

print("\n" + "=" * 70)
print("📋 v1.5.9 체크리스트")
print("-" * 50)
print("""
[상태 저장]
□ position 저장
□ entry_price 저장
□ sl_price / current_sl 저장
□ extreme_price 저장 ← 핵심!
□ trailing_active 저장

[상태 복구]
□ load_state에서 모든 값 복원
□ extreme_price 복원 → 진입가로 리셋 방지
□ self.exchange.position 동기화

[이어가기]
□ manage_position에서 복원된 extreme 사용
□ 트레일링 조건 즉시 체크
□ SL 상향 계속 진행
""")

print("\n결과 공유해줘")
