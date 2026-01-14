# verify_flow.py - 전체 시스템 흐름 검증
import os
import re

base_path = rstr(Path(__file__).parent)

print("=" * 60)
print("전체 시스템 흐름 검증 (A-Z)")
print("=" * 60)

# [1] 앱 시작 흐름
print("\n[1] 앱 시작 흐름")
main_path = os.path.join(base_path, 'GUI/staru_main.py')
if os.path.exists(main_path):
    with open(main_path, 'r', encoding='utf-8') as f:
        content = f.read()
    for check in ['license', 'update', 'TradingDashboard']:
        print(f"  {'OK' if check.lower() in content.lower() else 'X'} {check}")

# [2] 데이터 수집 흐름
print("\n[2] 데이터 수집 흐름")
files = {
    'core/unified_bot.py': ['_on_candle_close', 'df_entry_full', 'concat'],
    'exchanges/ws_handler.py': ['on_candle_close', 'reconnect'],
}
for file, keywords in files.items():
    path = os.path.join(base_path, file)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            c = f.read()
        missing = [k for k in keywords if k not in c]
        print(f"  {'OK' if not missing else 'X'} {file} {missing if missing else ''}")

# [3] 신호 감지 흐름
print("\n[3] 신호 감지 흐름")
strategy_path = os.path.join(base_path, 'core/strategy_core.py')
if os.path.exists(strategy_path):
    with open(strategy_path, 'r', encoding='utf-8') as f:
        sc = f.read()
    for func in ['detect_signal', 'run_backtest', 'calculate_atr']:
        print(f"  {'OK' if f'def {func}' in sc else 'X'} {func}()")

# [4] 진입 흐름
print("\n[4] 진입 흐름")
bot_path = os.path.join(base_path, 'core/unified_bot.py')
with open(bot_path, 'r', encoding='utf-8') as f:
    bc = f.read()
for check in ['execute_entry', 'set_leverage', 'place_market_order', 'stop_loss']:
    print(f"  {'OK' if check in bc else 'X'} {check}")

# [5] 포지션 관리
print("\n[5] 포지션 관리")
for check in ['trail_start_r', 'trail_dist_r', 'extreme_price', '_manage_position']:
    print(f"  {'OK' if check in bc else 'X'} {check}")

# [6] 청산 흐름
print("\n[6] 청산 흐름")
for check in ['_execute_live_close', 'pnl', 'save_trade', 'daily_pnl']:
    print(f"  {'OK' if check in bc else 'X'} {check}")

# [7] 파라미터 사용
print("\n[7] 파라미터 사용")
params = ['atr_mult', 'trail_start_r', 'trail_dist_r', 'filter_tf', 'entry_validity']
for param in params:
    count = bc.count(param)
    print(f"  {'OK' if count > 0 else 'X'} {param}: {count}회")

# [8] 계산식 확인
print("\n[8] 핵심 계산식")
if os.path.exists(strategy_path):
    with open(strategy_path, 'r', encoding='utf-8') as f:
        sc = f.read()
    print(f"  {'OK' if 'ewm' in sc or 'rolling' in sc else 'X'} 이동평균")
    print(f"  {'OK' if 'high' in sc and 'low' in sc else 'X'} ATR (H/L/C)")
print(f"  {'OK' if 'atr' in bc.lower() and 'atr_mult' in bc else 'X'} SL 계산")
print(f"  {'OK' if 'leverage' in bc else 'X'} 레버리지 적용")

print("\n" + "=" * 60)
print("흐름 검증 완료")
print("=" * 60)
