import sys
import os
import inspect

sys.path.insert(0, os.getcwd())

def check_methods():
    try:
        from exchanges.bybit_exchange import BybitExchange
        methods = ['get_current_candle', 'get_klines', 'connect', 'get_positions']
        print('=== BybitExchange 메서드 확인 ===')
        for m in methods:
            exists = hasattr(BybitExchange, m)
            print(f'{m}: {"✅" if exists else "❌"}')

        init_source = inspect.getsource(BybitExchange.__init__)
        has_session_none = 'self.session = None' in init_source
        print(f'\nsession in __init__: {"✅" if has_session_none else "❌"}')
        
    except ImportError:
        print("BybitExchange import failed")

def check_unified_bot_connect():
    try:
        from core.unified_bot import UnifiedBot
        source = inspect.getsource(UnifiedBot.run)
        has_connect = 'connect(' in source
        print(f'\nUnifiedBot.run calls connect(): {"✅" if has_connect else "❌"}')
        
        # Check __init__ too just in case
        init_source = inspect.getsource(UnifiedBot.__init__)
        has_connect_init = 'connect(' in init_source
        print(f'UnifiedBot.__init__ calls connect(): {"✅" if has_connect_init else "❌"}')
        
    except ImportError:
        print("UnifiedBot import failed")

if __name__ == "__main__":
    check_methods()
    check_unified_bot_connect()
