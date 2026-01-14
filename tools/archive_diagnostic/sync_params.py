"""백테스트 파라미터 추출 → 실매매 동기화"""
from pathlib import Path

base = Path(__file__).parent
strategy = base / 'core' / 'strategy_core.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔧 백테스트 기준값 추출 & 실매매 비교")
print("=" * 70)

params = ['atr_mult', 'pattern_tolerance', 'entry_validity', 'pullback_rsi', 
          'rsi_period', 'rsi_filter', 'trail', 'leverage']

# 1) 백테스트 기준값
print("\n[백테스트] strategy_core.py 기준값")
print("-" * 50)
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        for p in params:
            if p in lower and ('=' in line or ':' in line):
                print(f"  L{i}: {line.strip()[:80]}")
                break

# 2) 실매매 현재값
print("\n" + "-" * 70)
print("[실매매] unified_bot.py 현재값")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    found = []
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        for p in params:
            if p in lower and ('=' in line or ':' in line):
                found.append(f"  L{i}: {line.strip()[:80]}")
                break
    # 중복 제거 후 출력
    for f in found[:25]:
        print(f)
    if len(found) > 25:
        print(f"  ... 외 {len(found) - 25}개")

# 3) detect_signal vs _extract_all_signals 핵심 로직
print("\n" + "=" * 70)
print("🎯 패턴 감지 핵심 로직 비교")
print("=" * 70)

print("\n[백테스트] _extract_all_signals 핵심:")
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    in_func = False
    count = 0
    for i, line in enumerate(lines, 1):
        if 'def _extract_all_signals' in line:
            in_func = True
        if in_func and count < 40:
            if line.strip() and not line.strip().startswith('#'):
                print(f"  L{i}: {line.rstrip()[:85]}")
                count += 1
        if in_func and line.strip().startswith('def ') and count > 5:
            break

print("\n" + "-" * 70)
print("[실매매] detect_signal 핵심 (L3095~):")
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    in_func = False
    count = 0
    for i, line in enumerate(lines, 1):
        if 'def detect_signal' in line and i > 3000:
            in_func = True
        if in_func and count < 40:
            if line.strip() and not line.strip().startswith('#'):
                print(f"  L{i}: {line.rstrip()[:85]}")
                count += 1
        if in_func and line.strip().startswith('def ') and count > 5 and 'detect_signal' not in line:
            break

print("\n" + "=" * 70)
print("📋 불일치 항목 수동 확인 후 수정 진행")
