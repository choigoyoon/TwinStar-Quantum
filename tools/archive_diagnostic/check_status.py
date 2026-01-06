# Simplified project check
from pathlib import Path
import json

base = Path(r'C:\매매전략')

print("=== Project Status Check ===")

# 1. Version
print("\n[Version]")
ver = base / 'version.json'
if ver.exists():
    v = json.loads(ver.read_text(encoding='utf-8'))
    print(f"  {v.get('version')}")

# 2. Syntax check
print("\n[Syntax Check]")
files = [
    'core/unified_bot.py',
    'core/strategy_core.py',
    'exchanges/bybit_exchange.py',
]
for f in files:
    path = base / f
    if path.exists():
        try:
            code = path.read_bytes().decode('utf-8', errors='ignore')
            compile(code, f, 'exec')
            print(f"  OK: {f}")
        except SyntaxError as e:
            print(f"  ERR: {f} L{e.lineno}")

# 3. Key features
print("\n[v1.5.3 Features]")
bot = base / 'core/unified_bot.py'
code = bot.read_bytes().decode('utf-8', errors='ignore')

checks = [
    ('_record_trade', 'Trade Recording'),
    ('_get_compound_seed', 'Compounding'),
    ('existing_symbol', 'Symbol Check'),
    ('HAS_TRADE_HISTORY', 'TradeHistory Import'),
]
for kw, name in checks:
    status = 'OK' if kw in code else 'MISSING'
    print(f"  {status}: {name}")

# 4. Build files
print("\n[Build Files]")
spec = base / 'staru_clean.spec'
bat = base / 'build_clean_dist.bat'
print(f"  spec: {'OK' if spec.exists() else 'MISSING'}")
print(f"  bat: {'OK' if bat.exists() else 'MISSING'}")

print("\n=== Done ===")
