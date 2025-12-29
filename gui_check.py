from pathlib import Path
import re

base = Path(r'C:\매매전략')
gui = base / 'GUI'

print("=" * 70)
print("GUI Status Check")
print("=" * 70)

# 1. GUI files list
print("\n[1] GUI Files")
if gui.exists():
    for f in sorted(gui.glob('*.py')):
        try:
            lines = len(f.read_bytes().decode('utf-8', errors='ignore').split('\n'))
            print(f"  {f.name} ({lines} lines)")
        except:
            print(f"  {f.name} (error)")

# 2. Main file analysis
print("\n[2] staru_main.py Tabs")
main = gui / 'staru_main.py'
if main.exists():
    code = main.read_bytes().decode('utf-8', errors='ignore')
    tabs = re.findall(r'addTab\s*\(\s*\w+\s*,\s*["\']([^"\']+)["\']', code)
    if tabs:
        for t in tabs:
            print(f"  - {t}")

# 3. Widget features
print("\n[3] Widget Features Check")
widget_files = [
    'trading_dashboard.py',
    'backtest_widget.py', 
    'settings_widget.py',
    'optimization_widget.py',
    'data_download_widget.py',
    'dashboard_widgets.py',
]

for fname in widget_files:
    path = gui / fname
    if path.exists():
        code = path.read_bytes().decode('utf-8', errors='ignore')
        lines = len(code.split('\n'))
        
        features = []
        if 'QTableWidget' in code or 'QTableView' in code:
            features.append('Table')
        if 'matplotlib' in code.lower() or 'QChart' in code:
            features.append('Chart')
        if 'QPushButton' in code:
            features.append('Button')
        if 'emit(' in code:
            features.append('Signal')
        
        print(f"  OK: {fname} ({lines}L) [{', '.join(features) or 'Basic'}]")
    else:
        print(f"  MISSING: {fname}")

# 4. Hidden/Disabled features
print("\n[4] Hidden/Disabled Scan")
hidden_count = 0
for f in gui.glob('*.py'):
    try:
        code = f.read_bytes().decode('utf-8', errors='ignore')
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            if 'setVisible(False)' in line:
                print(f"  {f.name} L{i+1}: setVisible(False)")
                hidden_count += 1
            if '.hide()' in line and 'self.' in line and 'hide_menu' not in line.lower():
                print(f"  {f.name} L{i+1}: hide()")
                hidden_count += 1
    except:
        pass

if hidden_count == 0:
    print("  None found")

# 5. Core module imports
print("\n[5] Core Module Imports")
if main.exists():
    code = main.read_bytes().decode('utf-8', errors='ignore')
    modules = ['UnifiedBot', 'ExchangeManager', 'DataManager', 'strategy_core']
    for mod in modules:
        status = 'OK' if mod in code else 'MISSING'
        print(f"  {status}: {mod}")

print("\n" + "=" * 70)
print("Done")
