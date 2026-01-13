from pathlib import Path
import re

base = Path(r'C:\매매전략')
folders = ['core', 'exchanges']

print("FINDING MULTILINE ISSUES")

for folder in folders:
    folder_path = base / folder
    if folder_path.exists():
        for f in folder_path.glob('*.py'):
            try:
                code = f.read_text(encoding='utf-8', errors='ignore')
                
                # Check for except Exception:
     pass (multiline)
                matches = re.findall(r'except.*:\s*pass\s*$', code, re.MULTILINE)
                if matches:
                    print(f"SILENT_EXCEPT FOUND in {folder}/{f.name}")
                    # Find context
                    for m in matches:
                        print(f"  Match: {repr(m)}")
                
                # Check for risky API access
                lines = code.split('\n')
                for i, line in enumerate(lines):
                    if re.search(r'(result|response)\[["\']', line) and '.get(' not in line:
                        surrounding = '\n'.join(lines[max(0,min(len(lines)-1,i+1))]) # simplified
                        # check if inside try block (heuristic)
                        surrounding_context = '\n'.join(lines[max(0,i-3):i+1])
                        if 'try' not in surrounding_context:
                            print(f"RISK_ACCESS: {folder}/{f.name}:{i+1}: {line.strip()}")
            except Exception as e:
                print(f"ERROR reading {f.name}: {e}")

print("SEARCH COMPLETE")
