from pathlib import Path
import re
import sys

# Windows console encoding fix
sys.stdout.reconfigure(encoding='utf-8')

# updater 파일 찾기
base = Path(__file__).parent
files = list(base.rglob('*updat*.py'))

print("Updater 파일:")
for f in files:
    print(f"  {f}")

print("\n슬라이스 관련 코드 (의심 구간):")
print("=" * 50)

for f in files:
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        for i, line in enumerate(lines):
            # 딕셔너리/집합에서 슬라이스 사용 패턴
            # 예: dict[list[a:b]] -> Error
            if re.search(r'\[.*:.*\].*\[', line) or re.search(r'dict.*\[.*:\]', line) or re.search(r'\{.*:.*\}', line):
                 # Broad search for slice inside brackets
                 if '[' in line and ':' in line and ']' in line:
                     # Check if used as key? Hard to detect with regex perfectly, but let's print all slice usages
                     print(f"{f.name} L{i+1}: {line.strip()[:80]}")
    except Exception as e:
        print(f"Error reading {f}: {e}")
