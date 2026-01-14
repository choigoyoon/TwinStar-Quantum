# verify_zero.py - 매매 실패 제로 검증
import os
import re
import json
import sys

base_path = rstr(Path(__file__).parent)
sys.path.insert(0, base_path)

print("=" * 60)
print("매매 실패 제로 검증")
print("=" * 60)

critical = []
warning = []

# [A] 매매 핵심 흐름
print("\n[A] 매매 핵심 흐름")
core_funcs = [
    ('core/unified_bot.py', ['execute_entry', '_execute_live_close', '_on_candle_close']),
    ('core/strategy_core.py', ['run_backtest', 'detect_signal']),
]
for file, funcs in core_funcs:
    path = os.path.join(base_path, file)
    if not os.path.exists(path):
        critical.append(f"필수 파일 없음: {file}")
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for func in funcs:
        if f'def {func}' in content:
            print(f"  OK {file}: {func}()")
        else:
            critical.append(f"필수 함수 없음: {file} -> {func}()")

# [B] 데이터 흐름
print("\n[B] 데이터 흐름")
data_items = ['_load_full_historical_data', '_save_to_parquet', 'df_entry_full', 'df_pattern_full']
path = os.path.join(base_path, 'core/unified_bot.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()
for item in data_items:
    if item in content:
        print(f"  OK {item}")
    else:
        critical.append(f"데이터 흐름 누락: {item}")

# [C] 거래소 연결
print("\n[C] 거래소 연결")
ex_checks = [
    ('exchanges/bybit_exchange.py', ['connect', 'get_klines', 'place_market_order']),
    ('exchanges/binance_exchange.py', ['connect', 'get_klines']),
]
for file, funcs in ex_checks:
    path = os.path.join(base_path, file)
    if not os.path.exists(path):
        warning.append(f"거래소 파일 없음: {file}")
        continue
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for func in funcs:
        if f'def {func}' in content:
            print(f"  OK {file}: {func}()")
        else:
            warning.append(f"거래소 함수 없음: {file} -> {func}()")

# [D] 웹소켓 안정성
print("\n[D] 웹소켓 안정성")
ws_path = os.path.join(base_path, 'exchanges/ws_handler.py')
if os.path.exists(ws_path):
    with open(ws_path, 'r', encoding='utf-8') as f:
        ws_content = f.read().lower()
    ws_checks = ['reconnect', 'on_error', 'ping']
    for check in ws_checks:
        if check in ws_content:
            print(f"  OK {check}")
        else:
            warning.append(f"WS 누락: {check}")
else:
    warning.append("ws_handler.py 없음")

# [E] version.json
print("\n[E] version.json")
vj_path = os.path.join(base_path, 'version.json')
if os.path.exists(vj_path):
    with open(vj_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    if 'download_url' in data:
        print(f"  OK download_url")
    else:
        critical.append("version.json: download_url 없음")
    if 'version' in data or 'latest_version' in data:
        print(f"  OK version")
    else:
        critical.append("version.json: version 없음")

# [F] Import 테스트
print("\n[F] Import 테스트")
imports = ['core.unified_bot', 'core.strategy_core', 'exchanges.exchange_manager']
for mod in imports:
    try:
        __import__(mod)
        print(f"  OK {mod}")
    except Exception as e:
        critical.append(f"Import 실패: {mod}")

# 결과
print("\n" + "=" * 60)
print(f"치명적: {len(critical)}개, 경고: {len(warning)}개")
print("=" * 60)

print("\n[치명적]")
for c in critical:
    print(f"  X {c}")

print("\n[경고]")
for w in warning[:10]:
    print(f"  ! {w}")

print("\n" + "=" * 60)
if len(critical) == 0:
    print("OK 내부 문제 0개 - 매매 가능")
else:
    print("X 치명적 문제 있음 - 수정 필요")
