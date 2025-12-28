from pathlib import Path
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print(f"Base Directory: {base}")

# 1. version.json 확인
ver = base / 'version.json'
if ver.exists():
    print("version.json 내용 (Top 10 lines):")
    try:
        content = ver.read_text(encoding='utf-8')
        lines = content.split('\n')
        for i, line in enumerate(lines[:10]):
            print(f"{i+1}: {line}")
    except Exception as e:
        print(f"Error reading version.json: {e}")
else:
    print("version.json not found.")

# 2. updater 파일 실제 위치
print("\nupdater 파일:")
updater_found = False
for f in base.rglob('*updater*.py'):
    print(f"  {f}")
    if f.name == 'updater.py' and f.parent.name == 'core':
        updater_found = True

# 3. core/__init__.py 존재 여부
init = base / 'core/__init__.py'
print(f"\ncore/__init__.py 존재: {init.exists()}")
