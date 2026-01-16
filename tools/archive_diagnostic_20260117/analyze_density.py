import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

def count_lines(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except Exception:
        return 0

dirs = [
    str(PROJECT_ROOT / 'GUI'), 
    str(PROJECT_ROOT / 'core'), 
    str(PROJECT_ROOT / 'exchanges'),
    str(PROJECT_ROOT / 'utils'),
    str(PROJECT_ROOT / 'strategies'),
    str(Path(__file__).parent)
]

print("="*60)
print(f"{'PROJECT DENSITY AUDIT':^60}")
print("="*60)

for d in dirs:
    if not os.path.exists(d): continue
    print(f"\n📂 Directory: {d}")
    files = [f for f in os.listdir(d) if f.endswith('.py')]
    results = []
    for f in files:
        results.append((f, count_lines(os.path.join(d, f))))
    
    results.sort(key=lambda x: x[1], reverse=True)
    
    print(f"{'File Name':<35} | {'Lines':<10}")
    print("-" * 50)
    for f, l in results[:15]: # 상위 15개만 표시
        print(f"{f:<35} | {l:<10}")
    if len(results) > 15:
        print(f"... and {len(results)-15} more files.")
