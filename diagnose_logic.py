from pathlib import Path
import re

bot = Path(r'C:\매매전략\core\unified_bot.py')
try:
    code = bot.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')

    print("=" * 60)
    print("1. DataFrame 위험 패턴")
    print("=" * 60)

    df_issues = []
    for i, line in enumerate(lines):
        # if df or / if not df or / if df and
        # More specific regex to catch variable names starting with df_
        if re.search(r'if\s+.*df_.*(or|and)', line) or re.search(r'if\s+not\s+.*df_.*(or|and)', line):
            if 'is None' not in line and 'is not None' not in line and '.empty' not in line:
                df_issues.append((i+1, line.strip()))
                print(f"L{i+1}: {line.strip()[:100]}")

    print(f"\n→ 총 {len(df_issues)}개")

    print("\n" + "=" * 60)
    print("2. RSI 필터 로직")
    print("=" * 60)

    # RSI 조건 체크 로직 찾기
    for i, line in enumerate(lines):
        if 'Long조건' in line or 'Short조건' in line or 'pullback_rsi' in line:
            print(f"L{i+1}: {line.strip()[:100]}")

    print("\n" + "=" * 60)
    print("3. _check_entry_live 함수")
    print("=" * 60)

    # 함수 시작 찾기
    start = None
    for i, line in enumerate(lines):
        if 'def _check_entry_live' in line:
            start = i
            break

    if start:
        for i in range(start, min(start + 80, len(lines))):
            print(f"{i+1}: {lines[i]}")
            
except Exception as e:
    print(f"Error: {e}")
