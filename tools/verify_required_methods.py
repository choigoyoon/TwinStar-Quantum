import sys
sys.path.insert(0, rstr(Path(__file__).parent))

print('=== unified_bot.py 필수 메서드 검증 ===')
print()

# unified_bot.py에서 실제로 호출하는 메서드
required_calls = {
    'BotStateManager': ['load_state', 'save_state', 'save_trade'],
    'BotDataManager': ['load_historical', 'backfill', 'process_data', 'append_candle'],
    'SignalProcessor': ['get_trading_conditions', 'add_patterns_from_df'],
    'OrderExecutor': ['execute_entry', 'execute_close', 'last_position'],
    'PositionManager': ['check_entry_live', 'manage_live', 'sync_with_exchange']
}

from core.bot_state import BotStateManager
from core.data_manager import BotDataManager
from core.signal_processor import SignalProcessor
from core.order_executor import OrderExecutor
from core.position_manager import PositionManager

modules = {
    'BotStateManager': BotStateManager,
    'BotDataManager': BotDataManager,
    'SignalProcessor': SignalProcessor,
    'OrderExecutor': OrderExecutor,
    'PositionManager': PositionManager
}

missing = []

for mod_name, methods in required_calls.items():
    mod_class = modules[mod_name]
    print(f'[{mod_name}]')
    for m in methods:
        exists = hasattr(mod_class, m)
        status = '✅' if exists else '❌ MISSING'
        print(f'  {m}: {status}')
        if not exists:
            missing.append(f'{mod_name}.{m}')
    print()

print('=' * 50)
if missing:
    print(f'❌ 누락된 메서드 {len(missing)}개:')
    for m in missing:
        print(f'  - {m}')
    print()
    print('→ 이 메서드들 추가해야 함')
else:
    print('✅ 모든 필수 메서드 존재')
