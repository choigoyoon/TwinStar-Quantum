from pathlib import Path
import re

base = Path(r'C:\매매전략')
ex_path = base / 'exchanges'

print('=' * 70)
print('💱 Phase 1: 거래소 연동 점검')
print('=' * 70)

# 거래소 목록
exchanges = ['bybit', 'binance', 'okx', 'bitget', 'bingx', 'upbit', 'bithumb']

# 필수 기능
features = {
    'get_position': ['get_position', 'fetch_position', 'get_positions'],
    'get_balance': ['get_balance', 'fetch_balance'],
    'place_order': ['place_order', 'place_market_order', 'create_order'],
    'cancel_order': ['cancel_order', 'cancel_all'],
    'get_history': ['get_trade_history', 'fetch_my_trades', 'get_orders'],
    'set_leverage': ['set_leverage', 'leverage'],
    'websocket': ['start_websocket', 'websocket', 'ws_connect'],
    'position_mode': ['positionIdx', 'positionSide', 'posSide', 'hedge'],
}

print('\n📊 거래소별 기능 매트릭스')
print('-' * 70)
header = f"{'거래소':<12}"
for feat in features.keys():
    header += f"{feat:<14}"
print(header)
print('-' * 70)

results = {}
for ex in exchanges:
    ex_file = ex_path / f'{ex}_exchange.py'
    row = f"{ex:<12}"
    results[ex] = {}
    
    if ex_file.exists():
        code = ex_file.read_text(encoding='utf-8', errors='ignore')
        
        for feat, keywords in features.items():
            found = any(kw in code for kw in keywords)
            results[ex][feat] = found
            row += f"{'✅':<14}" if found else f"{'❌':<14}"
    else:
        for feat in features.keys():
            results[ex][feat] = None
            row += f"{'없음':<14}"
    
    print(row)

# 누락 기능 요약
print('\n⚠️ 누락 기능 요약')
print('-' * 70)
for ex, feats in results.items():
    missing = [f for f, v in feats.items() if v == False]
    if missing:
        print(f"  {ex}: {', '.join(missing)}")

# 선물 거래소 Position Mode 상세
print('\n🔧 선물 거래소 Position Mode 상세')
print('-' * 70)
futures_ex = ['bybit', 'binance', 'okx', 'bitget', 'bingx']
for ex in futures_ex:
    ex_file = ex_path / f'{ex}_exchange.py'
    if ex_file.exists():
        code = ex_file.read_text(encoding='utf-8', errors='ignore')
        has_idx = 'positionIdx' in code
        has_side = 'positionSide' in code
        has_pos = 'posSide' in code
        print(f"  {ex}: positionIdx={has_idx} positionSide={has_side} posSide={has_pos}")

print('\n' + '=' * 70)
