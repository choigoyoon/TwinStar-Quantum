import sys
import os
import inspect
import traceback

sys.path.insert(0, os.getcwd())

def run_verify_1_module_chain():
    print('=== 검증 1: 모듈 연결 체인 ===')
    print()

    try:
        from core.unified_bot import UnifiedBot
        
        modules = ['mod_state', 'mod_data', 'mod_signal', 'mod_order', 'mod_position']
        
        print('[UnifiedBot 모듈 연결]')
        source = inspect.getsource(UnifiedBot.__init__)
        # Also check _init_modular_components
        if hasattr(UnifiedBot, '_init_modular_components'):
            source += inspect.getsource(UnifiedBot._init_modular_components)

        for mod in modules:
            # Check if variable is assigned in __init__ or _init_modular_components
            connected = mod in source
            print(f'  {mod}: {"✅" if connected else "❌"}')
            
    except Exception as e:
        print(f'❌ UnifiedBot 로드 실패: {e}')
    
    print()

    print('[strategy_core 연결]')
    try:
        from core.signal_processor import SignalProcessor
        from core.position_manager import PositionManager
        
        sp_source = inspect.getsource(SignalProcessor)
        pm_source = inspect.getsource(PositionManager)
        
        print(f'  SignalProcessor → strategy_core: {"✅" if "strategy" in sp_source.lower() else "❌"}')
        print(f'  PositionManager → strategy_core: {"✅" if "strategy" in pm_source.lower() else "❌"}')
    except Exception as e:
        print(f'❌ 컴포넌트 로드 실패: {e}')

    print()

    print('[indicators.py 연결]')
    try:
        from core.data_manager import BotDataManager
        dm_source = inspect.getsource(BotDataManager)
        print(f'  DataManager → indicators: {"✅" if "indicators" in dm_source or "calculate_" in dm_source or "process_data" in dm_source else "❌"}')
    except Exception as e:
        print(f'❌ DataManager 로드 실패: {e}')
    print()


def run_verify_2_data_flow():
    print('=== 검증 2: 데이터 흐름 시뮬레이션 (로드 테스트) ===')
    print()
    
    # 1. DataManager
    try:
        from core.data_manager import BotDataManager
        print('1. BotDataManager 로드: ✅')
    except Exception as e:
        print(f'1. BotDataManager 로드: ❌ {e}')

    # 2. SignalProcessor
    try:
        from core.signal_processor import SignalProcessor
        sig = inspect.signature(SignalProcessor.__init__)
        print(f'2. SignalProcessor 로드: ✅ (params: {list(sig.parameters.keys())})')
    except Exception as e:
        print(f'2. SignalProcessor 로드: ❌ {e}')

    # 3. OrderExecutor
    try:
        from core.order_executor import OrderExecutor
        sig = inspect.signature(OrderExecutor.__init__)
        print(f'3. OrderExecutor 로드: ✅ (params: {list(sig.parameters.keys())})')
    except Exception as e:
        print(f'3. OrderExecutor 로드: ❌ {e}')

    # 4. PositionManager
    try:
        from core.position_manager import PositionManager
        sig = inspect.signature(PositionManager.__init__)
        print(f'4. PositionManager 로드: ✅ (params: {list(sig.parameters.keys())})')
    except Exception as e:
        print(f'4. PositionManager 로드: ❌ {e}')
    print()


def run_verify_3_unified_bot_mock():
    print('=== 검증 3: UnifiedBot 초기화 로직 확인 ===')
    print()
    
    try:
        from core.unified_bot import UnifiedBot
        
        init_params = inspect.signature(UnifiedBot.__init__).parameters
        print(f'UnifiedBot.__init__ 파라미터: {list(init_params.keys())}')
        
        source = inspect.getsource(UnifiedBot.__init__)
        if hasattr(UnifiedBot, '_init_modular_components'):
            source += inspect.getsource(UnifiedBot._init_modular_components)
        
        checks = {
            'BotStateManager': 'BotStateManager' in source,
            'BotDataManager': 'BotDataManager' in source,
            'SignalProcessor': 'SignalProcessor' in source,
            'OrderExecutor': 'OrderExecutor' in source,
            'PositionManager': 'PositionManager' in source
        }
        
        print()
        print('[모듈 초기화 확인]')
        for name, found in checks.items():
            print(f'  {name}: {"✅" if found else "❌"}')
        
        all_ok = all(checks.values())
        print()
        print(f'결론: {"✅ 모든 모듈 연결됨" if all_ok else "❌ 일부 모듈 누락"}')
        
    except Exception as e:
        print(f'❌ 에러: {e}')
        traceback.print_exc()

if __name__ == "__main__":
    run_verify_1_module_chain()
    run_verify_2_data_flow()
    run_verify_3_unified_bot_mock()
