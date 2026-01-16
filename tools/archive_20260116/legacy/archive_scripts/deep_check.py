"""
심층 불일치 탐지 스크립트
"""
import os

print("=" * 60)
print("🔍 숨겨진 불일치 심층 탐지")
print("=" * 60)

files = {
    'optimizer': 'core/optimizer.py',
    'backtest': 'GUI/backtest_widget.py',
    'live': 'core/unified_bot.py',
    'strategy': 'core/strategy_core.py'
}

# ===== 1. 초기 자본 설정 =====
print("\n🔴 [1] 초기 자본 설정")
print("-" * 40)
for name, path in files.items():
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if 'initial_capital' in line.lower() or ('capital' in line.lower() and '=' in line and 'def ' not in line):
            if not found:
                print(f"\n{name}:")
                found = True
            if '#' not in line[:5] and 'comment' not in line.lower():
                print(f"  L{i+1}: {line.strip()[:55]}")

# ===== 2. 레버리지 적용 =====
print("\n\n🔴 [2] 레버리지 적용")
print("-" * 40)
for name, path in files.items():
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    lev_count = content.lower().count('leverage')
    print(f"{name}: leverage {lev_count}회 사용")

# ===== 3. 포지션 사이즈 계산 =====
print("\n\n🔴 [3] 포지션 사이즈 계산")
print("-" * 40)

print("\nstrategy_core:")
with open('core/strategy_core.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
count = 0
for i, line in enumerate(lines):
    if ('size' in line.lower() or 'qty' in line.lower() or 'amount' in line.lower()) and '=' in line and 'def ' not in line:
        print(f"  L{i+1}: {line.strip()[:55]}")
        count += 1
        if count >= 5:
            break

print("\nunified_bot:")
with open('core/unified_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
count = 0
for i, line in enumerate(lines):
    if ('position_size' in line.lower() or 'order_size' in line.lower() or 'qty' in line.lower()) and '=' in line:
        print(f"  L{i+1}: {line.strip()[:55]}")
        count += 1
        if count >= 5:
            break

# ===== 4. 신호 만료 (validity) 처리 =====
print("\n\n🟡 [4] 신호 만료 (validity) 처리")
print("-" * 40)
for name, path in files.items():
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    found = False
    for i, line in enumerate(lines):
        if 'validity' in line.lower() or 'entry_validity' in line.lower():
            if not found:
                print(f"\n{name}:")
                found = True
            print(f"  L{i+1}: {line.strip()[:55]}")

# ===== 5. 지표 계산 시점 =====
print("\n\n🟡 [5] 지표 계산 시점")
print("-" * 40)

print("\nstrategy_core (백테스트):")
with open('core/strategy_core.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'add_all_indicators' in line or 'IndicatorGenerator' in line:
        print(f"  L{i+1}: {line.strip()[:55]}")

print("\nunified_bot (실매매):")
with open('core/unified_bot.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'add_all_indicators' in line or 'IndicatorGenerator' in line:
        print(f"  L{i+1}: {line.strip()[:55]}")

# ===== 6. 마지막 캔들 처리 =====
print("\n\n🟡 [6] 마지막 캔들 처리")
print("-" * 40)

with open('core/unified_bot.py', 'r', encoding='utf-8') as f:
    content = f.read()
if 'on_candle_close' in content:
    print("✅ unified_bot: on_candle_close 캔들 완성 체크 있음")
else:
    print("⚠️ unified_bot: 캔들 완성 체크 없음")

with open('core/strategy_core.py', 'r', encoding='utf-8') as f:
    content = f.read()
if 'iloc[-1]' in content:
    print("✅ strategy_core: iloc[-1] (마지막 캔들) 사용")
if 'iloc[-2]' in content:
    print("✅ strategy_core: iloc[-2] (완성된 캔들) 사용")

# ===== 결론 =====
print("\n" + "=" * 60)
print("📋 심층 분석 결과")
print("=" * 60)
