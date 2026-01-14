from pathlib import Path
import re

base = Path(__file__).parent
folders = ['core', 'exchanges']

print("FINDING REMAINING ISSUES")

for folder in folders:
    folder_path = base / folder
    if folder_path.exists():
        for f in folder_path.glob('*.py'):
            try:
                code = f.read_text(encoding='utf-8', errors='ignore')
                lines = code.split('\n')
                
                # Check for except Exception:
     pass
                for i, line in enumerate(lines):
                    if re.search(r'except.*:\s*pass\s*$', line):
                        print(f"SILENT_EXCEPT: {folder}/{f.name}:{i+1}: {line.strip()}")
                
                # Check for risky API access
                for i, line in enumerate(lines):
                    if re.search(r'(result|response)\[["\']', line) and '.get(' not in line:
                        surrounding = '\n'.join(lines[max(0,i-3):i+1])
                        if 'try' not in surrounding:
                            print(f"RISK_ACCESS: {folder}/{f.name}:{i+1}: {line.strip()}")
            except Exception as e:
                print(f"ERROR reading {f.name}: {e}")

print("SEARCH COMPLETE")
