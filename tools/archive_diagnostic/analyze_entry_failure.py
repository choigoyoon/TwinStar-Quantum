
from pathlib import Path
import sys

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print("=" * 60)
print("진입 실패 원인 분석")
print("=" * 60)

bot = base / 'core' / 'unified_bot.py'
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')

    # 1. _on_candle_close에서 execute_entry 호출 확인
    print("\n[1] 봉 마감 시 진입 호출 로직:")
    in_candle_close = False
    for i, line in enumerate(lines):
        if 'def _on_candle_close' in line:
            in_candle_close = True
        if in_candle_close:
            if 'execute_entry' in line:
                print(f"  L{i+1}: {line.strip()}")
            if 'pending' in line.lower():
                print(f"  L{i+1}: {line.strip()[:70]}")
            if in_candle_close and line.strip().startswith('def ') and '_on_candle_close' not in line:
                in_candle_close = False

    # 2. pending_signals 처리 로직
    print("\n[2] pending_signals 처리:")
    for i, line in enumerate(lines):
        if 'pending_signals' in line and ('pop' in line or 'clear' in line or 'remove' in line or '= []' in line or '.get(' in line):
            print(f"  L{i+1}: {line.strip()[:70]}")

    # 3. DataFrame or 연산 위치
    print("\n[3] DataFrame ambiguous 원인 (or 연산):")
    for i, line in enumerate(lines):
        if '.get(' in line and ' or ' in line:
            print(f"  L{i+1}: {line.strip()[:70]}")

    # 4. 봉 마감 → 진입 흐름
    print("\n[4] 봉 마감 후 실제 진입 조건:")
    for i, line in enumerate(lines):
        if 'candle' in line.lower() and 'close' in line.lower() and 'execute' in line.lower():
            # context_start = max(0, i-3) # simplified context
            # for j in range(context_start, min(i+5, len(lines))):
            print(f"  L{i+1}: {line.strip()[:70]}")
            # print()

    # 5. 진입 예정 로그 위치
    print("\n[5] '진입 예정' 로그 위치:")
    for i, line in enumerate(lines):
        if '진입 예정' in line:
            print(f"  L{i+1}: {line.strip()[:70]}")

    print("\n" + "=" * 60)
    print("예상 문제:")
    print("  1. pending_signals가 계속 쌓이기만 하고 처리 안 됨")
    print("  2. 봉 마감 시 execute_entry 호출 조건 불충족")
    print("  3. s.get('type') or 'default' → DataFrame일 때 에러")
    print("=" * 60)
else:
    print("❌ unified_bot.py not found")
