from pathlib import Path

bot = Path(r'C:\매매전략\core\unified_bot.py')
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

print("=" * 60)
print("수정 사항 최종 확인 (현재 코드 상태)")
print("=" * 60)

# 1. _execute_live_close 끝부분 (update_capital 호출 있는지)
print("\n[1] _execute_live_close 끝부분:")
for i, line in enumerate(lines):
    if 'def _execute_live_close' in line:
        # 함수 끝까지 찾기
        for j in range(i+1, min(i+400, len(lines))):
            if line.strip().startswith('def ') and j > i+5:
                # This logic is a bit flawed if it finds a nested def, but let's try to find next top-level def
                pass
            
            # Revised logic to find function end by indent
            indent = len(lines[i]) - len(lines[i].lstrip())
            
        # Let's just use a simpler way to find the end of the function
        # by looking for the next def at the same indent level or the end of file
        func_lines = []
        indent_level = None
        for j in range(i, len(lines)):
            line = lines[j]
            if not line.strip():
                func_lines.append((j+1, line))
                continue
            
            curr_indent = len(line) - len(line.lstrip())
            if indent_level is None:
                indent_level = curr_indent
            
            if j > i and curr_indent <= indent_level and line.strip().startswith('def '):
                break
            func_lines.append((j+1, line))
            if len(func_lines) > 300: break # safety
        
        # Print last 20 lines of the function
        for lnum, lcontent in func_lines[-25:]:
            print(f"L{lnum}: {lcontent}")
        break

# 2. trade_storage 구조
print("\n\n[2] trade_storage 클래스/모듈:")
for i, line in enumerate(lines):
    if 'trade_storage' in line and (('=' in line and 'self.' in line) or 'import' in line):
        print(f"L{i+1}: {line.strip()[:100]}")

# 3. get_trade_history import
print("\n\n[3] get_trade_history import:")
for i, line in enumerate(lines):
    if 'get_trade_history' in line and 'import' in line:
        print(f"L{i+1}: {line.strip()}")

# 4. _get_compound_seed 확인
print("\n\n[4] _get_compound_seed 현재 로직 (JSON 합산 여부):")
for i, line in enumerate(lines):
    if 'def _get_compound_seed' in line:
        for j in range(i, i+30):
            print(f"L{j+1}: {lines[j]}")
        break
