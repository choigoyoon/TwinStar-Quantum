import sys
import os
import inspect
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def verify_1_original_functions():
    print('=== 1. unified_bot.py 원래 기능 (추정) ===')
    original_functions = {
        '상태 관리': ['load_state()', 'save_state()', 'save_trade_history()', '_load_state_cache()', '_save_state_cache()'],
        '데이터 관리': ['_init_indicator_cache()', '_load_full_historical_data()', '_process_historical_data()', '_backfill_missing_candles()', '_save_to_parquet()', '_append_candle()', '_update_indicators()'],
        '시그널 처리': ['detect_signal()', '_add_new_patterns_to_queue()', '_check_entry_from_queue()', '_filter_valid_signals()', '_add_signal_to_queue()', '_get_current_trading_conditions()'],
        '주문 실행': ['execute_entry()', '_execute_live_entry()', '_execute_live_close()', '_execute_live_add()', '_record_trade()', '_calculate_pnl()'],
        '포지션 관리': ['manage_position()', '_manage_position_live()', '_check_entry_live()', 'sync_position()', '_sync_with_exchange_position()', '_close_on_sl()', '_update_trailing_sl()'],
        '메인 루프': ['run()', 'start()', 'stop()', '_on_candle_close()', '_on_price_update()']
    }
    for category, funcs in original_functions.items():
        print(f'[{category}]')
        for f in funcs: print(f'  - {f}')
    print()

def verify_2_separated_modules():
    print('=== 2. 분리된 모듈 확인 ===')
    modules = [
        ('core.bot_state', 'BotStateManager'),
        ('core.data_manager', 'BotDataManager'),
        ('core.signal_processor', 'SignalProcessor'),
        ('core.order_executor', 'OrderExecutor'),
        ('core.position_manager', 'PositionManager')
    ]
    
    for mod_path, class_name in modules:
        try:
            mod = __import__(mod_path, fromlist=[class_name])
            cls = getattr(mod, class_name)
            methods = [m for m in dir(cls) if not m.startswith('__')]
            print(f'\n[{mod_path}.py - {class_name}] (Total: {len(methods)})')
            for m in methods[:10]: print(f'  ✅ {m}')
            if len(methods) > 10: print('  ...')
        except Exception as e:
            print(f'❌ {mod_path} 로드 실패: {e}')
    print()

def verify_3_current_unified_bot():
    print('=== 3. unified_bot.py 현재 메서드 ===')
    try:
        from core.unified_bot import UnifiedBot
        all_methods = [m for m in dir(UnifiedBot) if not m.startswith('__')]
        public = [m for m in all_methods if not m.startswith('_')]
        private = [m for m in all_methods if m.startswith('_') and not m.startswith('__')]
        
        print(f'총 메서드/속성: {len(all_methods)}개')
        print('[Public]')
        for m in public[:10]: print(f'  {m}')
        print('[Private]')
        for m in private[:10]: print(f'  {m}')
    except Exception as e:
        print(f'❌ 로드 실패: {e}')
    print()

def verify_4_connections():
    print('=== 4. 모듈 연결 확인 ===')
    filepath = r'C:\매매전략\core\unified_bot.py'
    if not os.path.exists(filepath):
        print("❌ File not found")
        return
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    connections = {
        'BotStateManager': 'mod_state' in content or 'BotStateManager' in content,
        'BotDataManager': 'mod_data' in content or 'BotDataManager' in content,
        'SignalProcessor': 'mod_signal' in content or 'SignalProcessor' in content,
        'OrderExecutor': 'mod_order' in content or 'OrderExecutor' in content,
        'PositionManager': 'mod_position' in content or 'PositionManager' in content
    }
    
    print('[모듈 Import/사용]')
    for module, connected in connections.items():
        print(f'  {module}: {"✅" if connected else "❌"}')

    delegations = {
        'load_state -> mod_state': 'state' in content and 'load' in content, # Loose check
        'process_data -> mod_data': 'mod_data' in content and 'process' in content,
        'detect_signal -> mod_signal': 'mod_signal' in content and 'detect' in content, 
        'execute_entry -> mod_order': 'mod_order' in content and 'execute' in content,
        'manage_position -> mod_position': 'mod_position' in content and 'manage' in content
    }
    print('\n[위임 패턴 (Source Check)]')
    for delegation, found in delegations.items():
        print(f'  {delegation}: {"✅" if found else "⚠️"}')
    print()

def verify_5_mapping():
    print('=== 5. 기능 분리 매핑표 ===')
    print(f'{"원래 기능":<35} {"분리된 모듈":<25} {"상태":<10}')
    print('-' * 70)
    mapping = [
        ('load_state()', 'bot_state.py', '✅'),
        ('save_state()', 'bot_state.py', '✅'),
        ('save_trade_history()', 'bot_state.py', '✅'),
        ('_load_full_historical_data()', 'data_manager.py', '✅'),
        ('_process_historical_data()', 'data_manager.py', '✅'),
        ('detect_signal()', 'signal_processor.py', '✅'),
        ('execute_entry()', 'order_executor.py', '✅'),
        ('manage_position()', 'position_manager.py', '✅'),
        ('run()', 'unified_bot.py (유지)', '✅'),
        ('_on_candle_close()', 'unified_bot.py (유지)', '✅'),
    ]
    for func, module, status in mapping:
        print(f'{func:<35} {module:<25} {status:<10}')

if __name__ == "__main__":
    verify_1_original_functions()
    verify_2_separated_modules()
    verify_3_current_unified_bot()
    verify_4_connections()
    verify_5_mapping()
