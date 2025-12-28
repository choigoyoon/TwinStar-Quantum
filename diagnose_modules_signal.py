from pathlib import Path
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

# 1. updater 파일 위치 확인
print("1. Updater 파일 위치:")
for f in base.rglob('*updater*.py'):
    try:
        print(f"  {f.relative_to(base)}")
    except ValueError:
        print(f"  {f} (Not relative to base)")

# 2. core 폴더 내용 (init 확인 포함)
core = base / 'core'
if core.exists():
    print(f"\n2. core 폴더 내용:")
    for f in core.glob('*.py'):
        print(f"  {f.name}")

# 3. Signal 사용 방식 확인
bot = base / 'core/unified_bot.py'
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')

    print(f"\n3. L3060 주변 ({bot.name}):")
    # Search for execute_entry to be sure of location
    start_line = 0
    for i, line in enumerate(lines):
        if 'def execute_entry' in line:
            start_line = i
            break
            
    if start_line:
        # Print relevant block inside execute_entry
        for i in range(start_line + 30, start_line + 60):
            if i < len(lines):
                 # Mark the lines causing issues 
                 marker = "  "
                 if "signal.get" in lines[i] or "getattr(signal" in lines[i]:
                     marker = ">>"
                 print(f"{marker} {i+1}: {lines[i].strip()[:80]}")
    else:
        print("  execute_entry function not found.")
