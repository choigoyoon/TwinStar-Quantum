"""
Phase 10.2 검증 스크립트
"""
import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

print('=' * 60)
print('=== Phase 10.2 검증 결과 ===')
print('=' * 60)
print()

# 1. Import 검증
print('[1] Import 검증')
print('-' * 40)
modules = [
    'core.unified_bot',
    'core.bot_state',
    'core.data_manager',
    'core.signal_processor',
    'core.order_executor',
    'core.position_manager',
    'core.strategy_core',
    'GUI.trading_dashboard',
    'GUI.dashboard.multi_explorer',
    'GUI.optimization_widget',
    'GUI.backtest_widget',
]
import_success = 0
import_fail = 0
for m in modules:
    try:
        __import__(m)
        print(f'✅ {m}')
        import_success += 1
    except Exception as e:
        print(f'❌ {m}: {str(e)[:50]}')
        import_fail += 1

print()

# 2. Core 메서드 검증
print('[2] Core 메서드 검증')
print('-' * 40)
from core.bot_state import BotStateManager
from core.data_manager import BotDataManager
from core.signal_processor import SignalProcessor
from core.order_executor import OrderExecutor
from core.position_manager import PositionManager

checks = [
    (BotStateManager, ['load_state', 'save_state', 'save_trade']),
    (BotDataManager, ['load_historical', 'backfill', 'append_candle']),
    (SignalProcessor, ['get_trading_conditions', 'add_patterns_from_df']),
    (OrderExecutor, ['execute_entry', 'execute_close']),
    (PositionManager, ['sync_with_exchange', 'manage_live']),
]
method_success = 0
method_fail = 0
for cls, methods in checks:
    for m in methods:
        exists = hasattr(cls, m)
        status = '✅' if exists else '❌'
        print(f'{cls.__name__}.{m}: {status}')
        if exists:
            method_success += 1
        else:
            method_fail += 1

print()

# 3. GUI 로드 검증  
print('[3] GUI 로드 검증')
print('-' * 40)
try:
    from GUI.trading_dashboard import TradingDashboard
    from GUI.dashboard.multi_explorer import MultiExplorer
    from GUI.optimization_widget import OptimizationWidget
    from GUI.backtest_widget import BacktestWidget
    print('✅ 모든 GUI 모듈 로드 성공')
    gui_ok = True
except Exception as e:
    print(f'❌ GUI 로드 실패: {e}')
    gui_ok = False

print()

# 4. 파일 줄 수
print('[4] 파일 줄 수')
print('-' * 40)
files = [
    'GUI/trading_dashboard.py',
    'GUI/dashboard/multi_explorer.py',
    'GUI/optimization_widget.py',
    'GUI/backtest_widget.py',
    'core/unified_bot.py',
]
for f in files:
    full_path = os.path.join(str(Path(__file__).parent), f)
    if os.path.exists(full_path):
        with open(full_path, 'r', encoding='utf-8') as file:
            lines = len(file.readlines())
        print(f'{f}: {lines}줄')
    else:
        print(f'{f}: 파일 없음')

print()

# 최종 결과
print('=' * 60)
print('=== 최종 결과 ===')
print('=' * 60)
print(f'Import: {import_success}/{import_success + import_fail} 성공')
print(f'Methods: {method_success}/{method_success + method_fail} 성공')
print(f'GUI: {"✅" if gui_ok else "❌"}')

total_ok = import_fail == 0 and method_fail == 0 and gui_ok
if total_ok:
    print()
    print('✅ Phase 10.2 검증 통과 - Phase 10.3 진행 가능')
else:
    print()
    print('❌ 문제 발견 - 수정 필요')
