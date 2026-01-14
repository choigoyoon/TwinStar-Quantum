"""백테스트 수수료 적용 방식 확인"""
from pathlib import Path
import os
import sys

base = Path(__file__).parent
strategy = base / 'core' / 'strategy_core.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 백테스트 수수료 적용 방식 확인")
print("=" * 70)

# 1) strategy_core 수수료 로직
print("\n[1] strategy_core - 수수료 계산")
print("-" * 50)

if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        if 'fee' in lower or 'commission' in lower or '0.06' in line or '0.0006' in line:
            print(f"  L{i}: {line.strip()[:75]}")

# 2) 수수료 적용 시점
print("\n[2] 수수료 적용 시점 (진입/청산)")
print("-" * 50)

if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        if 'fee' in lower and ('entry' in lower or 'exit' in lower or 'open' in lower or 'close' in lower):
            print(f"  L{i}: {line.strip()[:75]}")
        if 'fee' in lower and '*' in line and '2' in line:
            print(f"  L{i}: {line.strip()[:75]} ← 왕복?")

# 3) PnL 계산에서 수수료 차감
print("\n[3] PnL에서 수수료 차감 로직")
print("-" * 50)

if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        if 'pnl' in lower and 'fee' in lower:
            print(f"  L{i}: {line.strip()[:75]}")
        if '-' in line and 'fee' in lower:
            print(f"  L{i}: {line.strip()[:75]}")

# 4) 백테스트 결과 계산
print("\n[4] run_backtest 내 수수료")
print("-" * 50)

if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    in_func = False
    for i, line in enumerate(lines, 1):
        if 'def run_backtest' in line:
            in_func = True
        if in_func:
            if line.strip().startswith('def ') and 'backtest' not in line.lower():
                in_func = False
                break
            if 'fee' in line.lower() or '0.06' in line or '0.0006' in line:
                print(f"  L{i}: {line.strip()[:70]}")

# 5) 프리셋/설정 파일
print("\n[5] 프리셋 수수료 설정")
print("-" * 50)

preset_files = list((base / 'presets').glob('*.json')) if (base / 'presets').exists() else []
preset_files += list(base.glob('*.json'))
import json
for pf in preset_files[:5]:
    try:
        data = json.loads(pf.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            if 'fee' in str(data).lower():
                for k, v in data.items():
                    if 'fee' in k.lower():
                        print(f"  {pf.name}: {k} = {v}")
                    if isinstance(v, dict):
                        for sk, sv in v.items():
                            if 'fee' in sk.lower():
                                print(f"  {pf.name} -> {k}: {sk} = {sv}")
    except Exception:

        pass

print("\n" + "=" * 70)
print("📋 수수료 정리")
print("-" * 50)
print("""
[바이빗 실제]
  Taker: 0.055% (편도)
  왕복: 0.055% × 2 = 0.11%

[백테스트 설정]
  0.06% → 편도? 왕복?
  
[확인 필요]
  - 0.06%가 1회 적용인지 2회 적용인지
  - PnL 계산 시 어떻게 차감되는지
""")

print("\n결과 공유해줘")
