from pathlib import Path
import re
import json

base = Path(__file__).parent
gui_dir = base / 'GUI'

print("="*40)
print("GUI DETAILED AUDIT")

if gui_dir.exists():
    for f in gui_dir.glob('*.py'):
        try:
            code = f.read_text(encoding='utf-8', errors='ignore')
            lines = code.split('\n')
            
            # except Exception:
     pass
            file_warnings = []
            for i, line in enumerate(lines):
                if re.search(r'except.*:\s*pass\s*$', line):
                    file_warnings.append(f"L{i+1}: {line.strip()}")
            
            # risky access
            file_risky = []
            for i, line in enumerate(lines):
                # Search for result['key'], state['key'], etc.
                if re.search(r'(result|response|state|data|info|params)\[["\']', line) and '.get(' not in line and '.update(' not in line:
                    # check if inside try block (heuristic)
                    surrounding = '\n'.join(lines[max(0,i-3):i+1])
                    if 'try' not in surrounding:
                        file_risky.append(f"L{i+1}: {line.strip()}")
            
            if file_warnings or file_risky:
                print(f"\nGUI/{f.name}:")
                for w in file_warnings:
                    print(f"  [PASS] {w}")
                for r in file_risky:
                    print(f"  [RISK] {r}")
        except Exception as e:
            print(f"ERROR reading {f.name}: {e}")

print("\nDEBUG END")
