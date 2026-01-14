
from pathlib import Path
import sys

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent
bot = base / 'core' / 'unified_bot.py'

if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')

    print("=" * 60)
    print("신호 중복 추가 로직 분석")
    print("=" * 60)

    # 1. 신호 추가 함수 찾기
    print("\n[1] 신호 추가 로직:")
    for i, line in enumerate(lines):
        if 'pending_signals' in line and ('append' in line or 'add' in line):
            # 앞뒤 컨텍스트
            start = max(0, i-5)
            end = min(len(lines), i+3)
            print(f"\n  L{i+1} 주변:")
            for j in range(start, end):
                marker = ">>>" if j == i else "   "
                print(f"  {marker} L{j+1}: {lines[j][:70]}")

    # 2. 중복 체크 로직 있는지
    print("\n[2] 중복 체크 로직:")
    has_dup_check = False
    for i, line in enumerate(lines):
        # Broaden search for duplicate logic
        if 'pending_signals' in line and ('if ' in lines[max(0,i-3):i+1] or 'not in' in line or 'already' in line.lower() or 'any(' in line):
             # Check if it looks like a check
             if 'any(' in line or 'for p in' in line:
                has_dup_check = True
                print(f"  L{i+1}: {line.strip()[:80]}")

    if not has_dup_check:
        print("  ❌ 중복 체크 없음 - 같은 신호 반복 추가됨")

    # 3. 신호 식별자 확인
    print("\n[3] 신호 고유 식별:")
    for i, line in enumerate(lines):
        if 'signal' in line.lower() and ('timestamp' in line.lower() or 'id' in line.lower() or 'time' in line.lower()):
            if 'def ' not in line and '#' not in line[:20]:
                print(f"  L{i+1}: {line.strip()[:60]}")
else:
    print("❌ unified_bot.py not found")
