from pathlib import Path
import re

base = Path(r'C:\매매전략')
folders = ['core', 'exchanges']

print("="*40)
print("DEBUGGING AUDIT")

for folder in folders:
    folder_path = base / folder
    if folder_path.exists():
        for f in folder_path.glob('*.py'):
            code = f.read_text(encoding='utf-8', errors='ignore')
            lines = code.split('\n')
            
            # except Exception:
     pass
            file_warnings = []
            matches = re.findall(r'except.*:\s*pass\s*$', code, re.MULTILINE)
            if matches:
                 # Find lines
                 for i, line in enumerate(lines):
                     if re.search(r'except.*:\s*pass\s*$', line):
                         file_warnings.append(f"L{i+1}: {line.strip()}")
            
            # risky access
            file_risky = []
            for i, line in enumerate(lines):
                if re.search(r'(result|response)\[["\']', line) and '.get(' not in line:
                    surrounding = '\n'.join(lines[max(0,i-3):i+1])
                    if 'try' not in surrounding:
                        file_risky.append(f"L{i+1}: {line.strip()}")
            
            if file_warnings or file_risky:
                print(f"\n{folder}/{f.name}:")
                for w in file_warnings:
                    print(f"  [PASS] {w}")
                for r in file_risky:
                    print(f"  [RISK] {r}")

print("\nDEBUG END")
