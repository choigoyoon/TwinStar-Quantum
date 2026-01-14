
import sys
import os
import inspect
from pathlib import Path

# Add project root
sys.path.insert(0, rstr(Path(__file__).parent))

print("=== STARTING GUI COMPREHENSIVE VERIFICATION ===\n")

# --- A. Display Elements ---
print("--- A. Display Elements ---")

# A1. Dashboard
try:
    with open(r'C:\매매전략\GUI\trading_dashboard.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    required_displays = {
        '현재가': ['current_price', 'price_label', 'last_price'],
        '포지션': ['position', 'pos_label', 'position_info'],
        '손익(PnL)': ['pnl', 'profit', 'unrealized'],
        '잔고': ['balance', 'equity', 'capital'],
        '레버리지': ['leverage', 'lev_'],
        '심볼': ['symbol', 'Symbol', 'BTCUSDT'],
        '거래소': ['exchange', 'Exchange', 'bybit'],
        '봇 상태': ['status', 'running', 'stopped', 'bot_status'],
        '차트': ['chart', 'candle', 'Chart', 'plot'],
        '로그': ['log', 'Log', 'text_log', 'log_widget']
    }
    
    print('[A1. Dashboard]')
    for name, patterns in required_displays.items():
        found = any(p in content for p in patterns)
        status = 'OK' if found else 'MISSING'
        print(f'{name}: {status}')
except Exception as e:
    print(f'[A1. Dashboard] Error: {e}')

# A2. Settings
try:
    settings_files = [
        r'C:\매매전략\GUI\settings_widget.py',
        r'C:\매매전략\GUI\staru_main.py'
    ]
    required_settings = {
        'API Key': ['api_key', 'apikey', 'API'],
        'Secret Key': ['secret', 'Secret'],
        '거래소 선택': ['exchange', 'Exchange'],
        '심볼 선택': ['symbol', 'Symbol'],
        '레버리지': ['leverage', 'Leverage'],
        '자본금': ['capital', 'Capital', 'initial'],
        '텔레그램': ['telegram', 'Telegram', 'bot_token']
    }
    
    print('\n[A2. Settings]')
    found_file = False
    for filepath in settings_files:
        if os.path.exists(filepath):
            found_file = True
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            for name, patterns in required_settings.items():
                found = any(p in content for p in patterns)
                status = 'OK' if found else 'MISSING'
                print(f'{name}: {status}')
            break
    if not found_file:
        print("Settings files not found")

except Exception as e:
    print(f'[A2. Settings] Error: {e}')

# A3. Optimization
try:
    filepath = r'C:\매매전략\GUI\optimization_widget.py'
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        required_opt = {
            '파라미터 슬라이더': ['slider', 'Slider', 'QSlider', 'SpinBox'],
            '진행률': ['progress', 'Progress', 'QProgressBar'],
            '결과 테이블': ['table', 'Table', 'QTableWidget'],
            '시작 버튼': ['start', 'Start', 'run', 'Run'],
            '중지 버튼': ['stop', 'Stop', 'cancel', 'Cancel'],
            '최적 파라미터': ['best', 'Best', 'optimal', 'result']
        }

        print('\n[A3. Optimization]')
        for name, patterns in required_opt.items():
            found = any(p in content for p in patterns)
            status = 'OK' if found else 'MISSING'
            print(f'{name}: {status}')
    else:
        print('\n[A3. Optimization] File not found')
except Exception as e:
    print(f'[A3. Optimization] Error: {e}')


# --- B. Data Binding ---
print("\n--- B. Data Binding ---")

# B1. Signal/Slot Patterns
try:
    with open(r'C:\매매전략\GUI\trading_dashboard.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    bindings = {
        '가격 업데이트': ['price_updated', 'on_price', 'update_price'],
        '포지션 업데이트': ['position_updated', 'on_position', 'update_position'],
        'PnL 업데이트': ['pnl_updated', 'on_pnl', 'update_pnl'],
        '캔들 업데이트': ['candle_updated', 'on_candle', 'new_candle'],
        '시그널 업데이트': ['signal_updated', 'on_signal', 'new_signal'],
        '로그 업데이트': ['log_updated', 'append_log', 'add_log']
    }
    
    print('[B1. GUI Slots]')
    for name, patterns in bindings.items():
        found = any(p in content for p in patterns)
        status = 'OK' if found else 'CHECK'
        print(f'{name}: {status}')
except Exception as e:
    print(f'[B1. GUI Slots] Error: {e}')

# B2. Core -> GUI Flow
try:
    # Need to check UnifiedBot for signals/callbacks
    try:
        from core.unified_bot import UnifiedBot
        callback_patterns = ['callback', 'emit', 'signal', 'notify', 'on_']
        methods = [m for m in dir(UnifiedBot) if any(p in m.lower() for p in callback_patterns)]
        
        print('\n[B2. Core Callbacks]')
        if methods:
            print(f'Methods found: {len(methods)} ({methods[:3]}...)')
            print('Core -> GUI Data Flow: OK')
        else:
            print('Core -> GUI Data Flow: CHECK (No obvious callback methods)')
    except ImportError:
        print('\n[B2. Core Callbacks] Could not import UnifiedBot')
except Exception as e:
    print(f'[B2. Core Callbacks] Error: {e}')


# --- C. External Dependencies ---
print("\n--- C. External Dependencies ---")

# C1. Exchange API
try:
    try:
        from exchanges.bybit_exchange import BybitExchange
        api_methods = {
            '잔고 조회': 'get_balance',
            '포지션 조회': 'get_positions',
            '주문 실행': 'place_order',
            '주문 취소': 'cancel_order',
            '시장가 주문': 'market_order',
            '지정가 주문': 'limit_order',
            '웹소켓 연결': 'connect',
            '레버리지 설정': 'set_leverage'
        }
        print('[C1. Exchange API]')
        for name, method in api_methods.items():
            exists = hasattr(BybitExchange, method)
            status = 'OK' if exists else 'MISSING'
            print(f'{name} ({method}): {status}')
    except ImportError:
        print('[C1. Exchange API] Could not import BybitExchange')
except Exception as e:
    print(f'[C1. Exchange API] Error: {e}')

# C2. Telegram
try:
    print('\n[C2. Telegram]')
    tg_patterns = ['telegram', 'notifier', 'notification']
    found_files = []
    
    for root, dirs, files in os.walk(rstr(Path(__file__).parent)):
        if '__pycache__' in root:
            continue
        for f in files:
            if f.endswith('.py'):
                if any(p in f.lower() for p in tg_patterns):
                    found_files.append(f)
    
    if found_files:
        print(f'Telegram related files: {len(found_files)} found')
        print(f'Sample: {found_files[:3]}')
    else:
        # Grep fallback
        import subprocess
        try:
            result = subprocess.check_output('findstr /s /i "telegram" C:\\매매전략\\*.py', shell=True).decode('utf-8', errors='ignore')
            if 'telegram' in result.lower():
                print('Telegram Code: Found via grep')
            else:
                print('Telegram Code: MISSING')
        except Exception:
             print('Telegram Code: MISSING')
except Exception as e:
    print(f'[C2. Telegram] Error: {e}')

# C3. Storage
try:
    print('\n[C3. Storage]')
    storage_checks = {
        'Parquet 저장': r'C:\매매전략\data',
        '상태 파일': r'C:\매매전략\storage',
        '로그 파일': r'C:\매매전략\logs',
        '설정 파일': r'C:\매매전략\config'
    }
    
    for name, path in storage_checks.items():
        exists = os.path.exists(path)
        status = 'OK' if exists else 'MISSING'
        print(f'{name}: {status}')
except Exception as e:
    print(f'[C3. Storage] Error: {e}')


# --- D. Error Handling ---
print("\n--- D. Error Handling ---")

# D1. Error Display
try:
    with open(r'C:\매매전략\GUI\trading_dashboard.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    error_patterns = {
        '에러 팝업': ['QMessageBox', 'critical', 'warning'],
        '에러 로그': ['logger.error', 'logging.error', '.error('],
        '상태 표시': ['status_label', 'error_label', 'statusBar'],
        '연결 끊김': ['disconnected', 'connection_lost', 'reconnect'],
        '예외 처리': ['try:', 'except ', 'Exception']
    }
    
    print('[D1. Error Display]')
    for name, patterns in error_patterns.items():
        found = any(p in content for p in patterns)
        status = 'OK' if found else 'MISSING'
        print(f'{name}: {status}')
    
    print(f"Exception Blocks: {content.count('except ')}")
except Exception as e:
    print(f'[D1. Error Display] Error: {e}')

# D2. Recovery
try:
    print('\n[D2. Recovery]')
    recovery_files = [
        r'C:\매매전략\core\unified_bot.py',
        r'C:\매매전략\exchanges\bybit_exchange.py'
    ]
    recovery_patterns = {
        '재연결': ['reconnect', 'retry', 'Retry'],
        '상태 복구': ['restore', 'recover', 'load_state'],
        '자동 재시작': ['restart', 'auto_start'],
        '백오프': ['backoff', 'delay', 'sleep']
    }
    
    for filepath in recovery_files:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f'[{os.path.basename(filepath)}]')
            for name, patterns in recovery_patterns.items():
                found = any(p in content for p in patterns)
                print(f'  {name}: {"OK" if found else "-"}')
except Exception as e:
    print(f'[D2. Recovery] Error: {e}')


# --- E. Layout ---
print("\n--- E. Layout ---")

# E1. Tabs
try:
    with open(r'C:\매매전략\GUI\staru_main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    tab_patterns = {
        '탭 위젯': ['QTabWidget', 'TabWidget'],
        '대시보드 탭': ['dashboard', 'Dashboard', 'trading'],
        '최적화 탭': ['optim', 'Optim'],
        '설정 탭': ['setting', 'Setting', 'config'],
        '백테스트 탭': ['backtest', 'Backtest']
    }
    
    print('[E1. Tabs]')
    for name, patterns in tab_patterns.items():
        found = any(p in content for p in patterns)
        status = 'OK' if found else 'MISSING'
        print(f'{name}: {status}')
except Exception as e:
    print(f'[E1. Tabs] Error: {e}')

# E2. Widget Stats
try:
    with open(r'C:\매매전략\GUI\trading_dashboard.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    widgets = {
        'QLabel': content.count('QLabel'),
        'QPushButton': content.count('QPushButton'),
        'QLineEdit': content.count('QLineEdit'),
        'QComboBox': content.count('QComboBox'),
        'QTableWidget': content.count('QTableWidget'),
        'QTextEdit': content.count('QTextEdit'),
        'QSlider': content.count('QSlider'),
        'QSpinBox': content.count('QSpinBox'),
        'QCheckBox': content.count('QCheckBox')
    }
    
    print('\n[E2. Widget Stats]')
    for w, c in widgets.items():
        print(f'{w}: {c}')
    print(f"Total Widgets: {sum(widgets.values())}")
except Exception as e:
    print(f'[E2. Widget Stats] Error: {e}')

print("\n=== VERIFICATION COMPLETE ===")
