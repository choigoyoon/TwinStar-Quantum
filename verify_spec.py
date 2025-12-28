import os
import sys
sys.path.insert(0, r'C:\매매전략')

# 1. 필수 파일 확인
files = [
    'GUI/staru_main.py',
    'GUI/styles.qss',
    'config/presets',
    'locales/ko.json',
    'version.txt',
]

print('=== 필수 파일 확인 ===')
for f in files:
    path = os.path.join(r'C:\매매전략', f)
    exists = os.path.exists(path)
    status = '✅' if exists else '❌'
    print(f'{status} {f}')

# 2. 모듈 import 테스트
modules = [
    'core.unified_bot',
    'core.multi_trader', 
    'core.multi_sniper',
    'core.strategy_core',
    'core.optimizer',
    'exchanges.bybit_exchange',
    'exchanges.binance_exchange',
    'exchanges.exchange_manager',
    'exchanges.ws_handler',
    'GUI.trading_dashboard',
]

print('\n=== 모듈 import 테스트 ===')
for m in modules:
    try:
        __import__(m)
        print(f'✅ {m}')
    except Exception as e:
        print(f'❌ {m}: {str(e)[:40]}')
