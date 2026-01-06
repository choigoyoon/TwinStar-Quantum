
import sys
import os

# Add project root
sys.path.insert(0, r'C:\매매전략')

print("=== STARTING REQUIREMENTS VERIFICATION ===\n")

# --- 1. Existing Position Filtering ---
print("--- 1. Existing Position Filtering ---")

# 1.1 Position Query Logic
try:
    filepath = r'C:\매매전략\core\unified_bot.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    checks = {
        'get_positions 호출': 'get_positions' in content,
        '포지션 필터링': 'filter' in content.lower() and 'position' in content.lower(),
        '심볼 비교': 'symbol' in content and '==' in content,
        '봇 ID 구분': 'bot_id' in content or 'client_id' in content or 'order_id' in content,
        '기존 포지션 제외': 'exclude' in content.lower() or 'skip' in content.lower()
    }

    print('[1.1 Position Query Logic]')
    for name, exists in checks.items():
        status = 'OK' if exists else 'MISSING'
        print(f'{name}: {status}')
except Exception as e:
    print(f'[1.1 Error]: {e}')

# 1.2 Bot Position Tracking
try:
    files = [
        r'C:\매매전략\core\bot_state.py',
        r'C:\매매전략\core\position_manager.py',
        r'C:\매매전략\core\order_executor.py'
    ]

    tracking_patterns = {
        'position_id': ['position_id', 'pos_id'],
        'order_id 저장': ['order_id', 'orderId'],
        'client_order_id': ['client_order_id', 'clientOrderId', 'clOrdId'],
        '봇 생성 표시': ['created_by', 'bot_created', 'is_bot']
    }

    print('\n[1.2 Bot Position Tracking]')
    for filepath in files:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f'[{os.path.basename(filepath)}]')
            for name, patterns in tracking_patterns.items():
                found = any(p in content for p in patterns)
                status = 'OK' if found else '-'
                print(f'  {name}: {status}')
except Exception as e:
    print(f'[1.2 Error]: {e}')


# --- 2. GUI Position Display ---
print("\n--- 2. GUI Position Display ---")

# 2.1 GUI Source
try:
    filepath = r'C:\매매전략\GUI\trading_dashboard.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    sources = {
        '거래소 직접 조회': 'exchange.get_positions' in content or 'get_positions()' in content,
        '봇 상태에서': 'bot.position' in content or 'bot_state' in content,
        '자체 추적': 'self.position' in content or 'current_position' in content,
        '필터링 로직': 'filter' in content.lower() and 'position' in content.lower()
    }

    print('[2.1 GUI Position Source]')
    for name, exists in sources.items():
        status = 'OK' if exists else '-'
        print(f'{name}: {status}')

    # Widget check
    if 'position' in content.lower():
        pos_count = content.lower().count('position')
        print(f'position keyword count: {pos_count}')
except Exception as e:
    print(f'[2.1 Error]: {e}')

# 2.2 Self Tracking Logic
try:
    filepath = r'C:\매매전략\core\position_manager.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    self_tracking = {
        'self.position 저장': 'self.position' in content,
        'Position 클래스': 'class Position' in content or 'Position(' in content,
        '진입 시 저장': 'entry' in content.lower() and 'save' in content.lower(),
        '청산 시 제거': 'close' in content.lower() or 'exit' in content.lower()
    }

    print('\n[2.2 Self Tracking Logic]')
    for name, exists in self_tracking.items():
        status = 'OK' if exists else 'CHECK'
        print(f'{name}: {status}')
except Exception as e:
    print(f'[2.2 Error]: {e}')


# --- 3. Trade History/Profit Calculation ---
print("\n--- 3. Trade History/Profit Calculation ---")

# 3.1 Exchange History API
try:
    exchanges = ['bybit', 'binance', 'okx', 'bitget']
    history_methods = ['get_trade_history', 'get_orders', 'get_closed_orders', 
                       'get_fills', 'get_executions', 'fetch_my_trades']

    print('[3.1 Exchange History API]')
    for ex in exchanges:
        filepath = fr'C:\매매전략\exchanges\{ex}_exchange.py'
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            found_methods = [m for m in history_methods if m in content]
            if found_methods:
                print(f'{ex}: {found_methods}')
            else:
                print(f'{ex}: No history API found')
except Exception as e:
    print(f'[3.1 Error]: {e}')

# 3.2 PnL Calculation Style
try:
    filepath = r'C:\매매전략\core\order_executor.py'
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    pnl_methods = {
        '자체 계산': 'calculate_pnl' in content,
        '거래소 PnL 사용': 'realized_pnl' in content.lower() or 'realised' in content.lower(),
        '수수료 반영': 'fee' in content.lower() or 'commission' in content.lower(),
        '복리 계산': 'compound' in content.lower() or 'cumulative' in content.lower()
    }

    print('\n[3.2 PnL Calculation Style]')
    for name, exists in pnl_methods.items():
        status = 'OK' if exists else 'MISSING'
        print(f'{name}: {status}')
except Exception as e:
    print(f'[3.2 Error]: {e}')

# 3.3 Trade Storage
try:
    filepath = r'C:\매매전략\storage\trade_storage.py'
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        storage_checks = {
            '거래 저장': 'save' in content.lower() and 'trade' in content.lower(),
            '거래 로드': 'load' in content.lower() and 'trade' in content.lower(),
            '실제 PnL 저장': 'pnl' in content.lower() or 'profit' in content.lower(),
            '거래소 ID 저장': 'order_id' in content or 'trade_id' in content
        }
        
        print('\n[3.3 Trade Storage]')
        for name, exists in storage_checks.items():
            status = 'OK' if exists else 'CHECK'
            print(f'{name}: {status}')
    else:
        print('\n[3.3 Trade Storage] File not found')
except Exception as e:
    print(f'[3.3 Error]: {e}')

# 3.4 Compound Interest
try:
    files = [
        r'C:\매매전략\core\strategy_core.py',
        r'C:\매매전략\core\order_executor.py',
        r'C:\매매전략\GUI\trading_dashboard.py'
    ]

    compound_patterns = {
        '복리': ['compound', 'cumulative', '복리'],
        '누적 수익': ['total_profit', 'cumulative_pnl', 'running_pnl'],
        '잔고 기반': ['balance', 'equity', 'capital'],
        '퍼센트 계산': ['percent', 'pct', '%']
    }

    print('\n[3.4 Compound Interest]')
    for filepath in files:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f'[{os.path.basename(filepath)}]')
            for name, patterns in compound_patterns.items():
                found = any(p in content for p in patterns)
                status = 'OK' if found else '-'
                print(f'  {name}: {status}')
except Exception as e:
    print(f'[3.4 Error]: {e}')

print("\n=== VERIFICATION COMPLETE ===")
