from pathlib import Path

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

print("=" * 60)
print("복리 시드 실제 코드 확인")
print("=" * 60)

# 1. _get_compound_seed 함수 전체
print("\n[1] _get_compound_seed 함수:")
start = None
for i, line in enumerate(lines):
    if 'def _get_compound_seed' in line:
        start = i
        break

if start is not None:
    indent = None
    for j in range(start, len(lines)):
        line = lines[j]
        if indent is None and line.strip():
            # Get indent of the definition
            indent_match = len(line) - len(line.lstrip())
            indent = indent_match
        
        # Stop if we hit another function at same or less indent
        if j > start and line.strip().startswith('def '):
            curr_indent = len(line) - len(line.lstrip())
            if curr_indent <= indent:
                break
        
        print(f"L{j+1}: {line}")
        if j > start + 50: # safety
            break
else:
    print("  X 함수 없음")

# 2. 어디서 호출되는지
print("\n\n[2] _get_compound_seed 호출 위치:")
for i, line in enumerate(lines):
    if '_get_compound_seed' in line and 'def ' not in line:
        print(f"L{i+1}: {line.strip()[:100]}")

# 3. trade 기록 후 자본 업데이트
print("\n\n[3] 거래 종료 후 자본 업데이트:")
for i, line in enumerate(lines):
    l_lower = line.lower()
    if 'update_capital' in l_lower or ('capital' in l_lower and '+=' in line):
        print(f"L{i+1}: {line.strip()[:100]}")

# 4. JSON vs SQLite 저장
print("\n\n[4] 거래 기록 저장:")
for i, line in enumerate(lines):
    l_lower = line.lower()
    if 'trade_storage' in l_lower or 'sqlite' in l_lower or 'save_trade' in l_lower:
        print(f"L{i+1}: {line.strip()[:100]}")
