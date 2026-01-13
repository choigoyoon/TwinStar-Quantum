from pathlib import Path
import re

base = Path(r'C:\매매전략')
folders = ['core', 'exchanges']

print("DEBUG: LISTING EVERY WARNING LINE")

for folder in folders:
    folder_path = base / folder
    if folder_path.exists():
        for f in folder_path.glob('*.py'):
            code = f.read_text(encoding='utf-8', errors='ignore')
            lines = code.split('\n')
            
            # except Exception:
     pass
            for i, line in enumerate(lines):
                if re.search(r'except.*:\s*pass\s*$', line):
                     print(f"PASS: {folder}/{f.name}:{i+1}: {line.strip()}")
            
            # unsafe access
            for i, line in enumerate(lines):
                if re.search(r'(result|response)\[["\']', line) and '.get(' not in line:
                    surrounding = '\n'.join(lines[max(0,i-3):i+1])
                    if 'try' not in surrounding:
                        print(f"RISK: {folder}/{f.name}:{i+1}: {line.strip()}")

print("DEBUG: END")
