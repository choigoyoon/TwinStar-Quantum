from pathlib import Path
import re

base = Path(__file__).parent
folders = ['core', 'exchanges']

print("LOCATING MULTILINE ISSUES WITH LINE NUMBERS")

for folder in folders:
    folder_path = base / folder
    if folder_path.exists():
        for f in folder_path.glob('*.py'):
            try:
                code = f.read_text(encoding='utf-8', errors='ignore')
                lines = code.split('\n')
                
                # Use a sliding window or a more advanced search to find multiline except Exception:
     pass
                # We know they look like except ...:\n\s*pass
                for i in range(len(lines) - 1):
                    if re.search(r'except.*:', lines[i]) and re.search(r'^\s*pass\s*$', lines[i+1]):
                        print(f"MULTILINE_EXCEPT: {folder}/{f.name}:{i+1} -> {i+2}")
                        print(f"  {i+1}: {lines[i].strip()}")
                        print(f"  {i+2}: {lines[i+1].strip()}")
            except Exception as e:
                print(f"ERROR reading {f.name}: {e}")

print("SEARCH COMPLETE")
