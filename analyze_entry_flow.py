
from pathlib import Path
import sys

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')
bot = base / 'core' / 'unified_bot.py'

if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')

    print("=" * 60)
    print("진입 예정 → 실제 진입 추적")
    print("=" * 60)

    # 1. "진입 예정" 로그 위치
    print("\n[1] '진입 예정' 출력 위치:")
    for i, line in enumerate(lines):
        if '진입 예정' in line or '진입예정' in line:
            print(f"  L{i+1}: {line.strip()[:60]}")
            # 이 함수 내에서 execute_entry 호출하는지
            start = i
            for j in range(i, min(i+30, len(lines))):
                if 'execute_entry' in lines[j]:
                    print(f"  → L{j+1}: {lines[j].strip()[:60]}")
                if lines[j].strip().startswith('def ') and j > i:
                    break

    # 2. _on_candle_close 내용
    print("\n[2] _on_candle_close 전체 흐름:")
    in_func = False
    for i, line in enumerate(lines):
        if 'def _on_candle_close' in line:
            in_func = True
            print(f"\n  L{i+1}: {line.strip()}")
        if in_func:
            # 핵심 키워드만
            if any(k in line for k in ['execute_entry', 'pending', 'signal', 'entry', 'return', 'if ', 'else']):
                print(f"  L{i+1}: {line.strip()[:70]}")
            if in_func and line.strip().startswith('def ') and '_on_candle_close' not in line:
                break

    # 3. execute_entry 호출 조건
    print("\n[3] execute_entry 호출부:")
    for i, line in enumerate(lines):
        if 'execute_entry(' in line and 'def ' not in line:
            # 앞 5줄 (조건문)
            print(f"\n  호출 L{i+1}:")
            for j in range(max(0, i-5), i+1):
                print(f"    L{j+1}: {lines[j].strip()[:60]}")
else:
    print("❌ unified_bot.py not found")
