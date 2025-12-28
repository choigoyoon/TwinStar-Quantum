# verify_import.py - 실제 Import 테스트
import sys
import os
from pathlib import Path

base = Path(r'C:\매매전략')
sys.path.insert(0, str(base))
os.chdir(base)

print("=" * 60)
print("실제 Import 테스트")
print("=" * 60)

errors = []
success = []

modules = [
    ('json', 'import json'),
    ('Path', 'from pathlib import Path'),
    ('exchange_manager', 'from exchanges.exchange_manager import ExchangeManager'),
    ('bybit', 'from exchanges.bybit_exchange import BybitExchange'),
    ('indicator', 'from indicator_generator import IndicatorGenerator'),
    ('strategy_core', 'import core.strategy_core'),
    ('unified_bot', 'from core.unified_bot import UnifiedBot'),
    ('updater', 'from core.updater import Updater'),
    ('multi_sniper', 'from core.multi_sniper import MultiCoinSniper'),
    ('multi_trader', 'from core.multi_trader import MultiTrader'),
    ('PyQt5', 'from PyQt5.QtWidgets import QApplication'),
]

for name, stmt in modules:
    try:
        exec(stmt)
        success.append(name)
        print(f"OK {name}")
    except Exception as e:
        errors.append((name, str(e)[:80]))
        print(f"X {name}: {str(e)[:80]}")

print("\n" + "=" * 60)
print(f"결과: {len(success)}/{len(modules)}")

if errors:
    print("\n실패 목록:")
    for name, err in errors:
        print(f"  {name}: {err}")
else:
    print("\nOK 모든 모듈 import 성공")
