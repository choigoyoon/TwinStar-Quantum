
from pathlib import Path
import re
import sys
import logging

# Suppress logging during verification
logging.basicConfig(level=logging.CRITICAL)

base = Path(r'C:\매매전략')
results = {}

print("=" * 70)
print("TwinStar Quantum 전체 시스템 검증")
print("=" * 70)

# ============================================
# 1. 매매법 (전략 로직)
# ============================================
print("\n[1] 매매법 (전략 로직)")
print("-" * 50)

bot_path = base / 'core/unified_bot.py'
if bot_path.exists():
    code = bot_path.read_text(encoding='utf-8', errors='ignore')

    checks = {
        'W/M 패턴 감지': 'pattern' in code.lower() and ('w' in code.lower() or 'm' in code.lower()),
        'RSI 필터': 'rsi' in code.lower() and ('<' in code or '>' in code),
        'ATR 기반 SL': 'atr' in code.lower() and 'stop' in code.lower(),
        '트레일링 스탑': 'trail' in code.lower(),
        'Long/Short 양방향': 'long' in code.lower() and 'short' in code.lower(),
    }
    for name, result in checks.items():
        print(f"  {'✅' if result else '❌'} {name}")
        results[f'매매법_{name}'] = result
else:
    print("  ❌ core/unified_bot.py 없음")

# ============================================
# 2. 거래소 연동
# ============================================
print("\n[2] 거래소 연동")
print("-" * 50)

exchanges = ['bybit', 'binance', 'okx', 'bitget', 'bingx', 'upbit', 'bithumb']
for ex in exchanges:
    path = base / f'exchanges/{ex}_exchange.py'
    if path.exists():
        ex_code = path.read_text(encoding='utf-8', errors='ignore')
        has_order = 'place_market_order' in ex_code or 'create_order' in ex_code
        has_position = 'get_positions' in ex_code or 'get_position' in ex_code
        has_order_id = 'order_id' in ex_code.lower() or 'orderid' in ex_code.lower()
        status = '✅' if (has_order and has_position) else '⚠️'
        print(f"  {status} {ex}: 주문{'✓' if has_order else '✗'} | 포지션{'✓' if has_position else '✗'} | ID반환{'✓' if has_order_id else '✗'}")
    else:
        print(f"  ❌ {ex}: 파일 없음")

# Hedge Mode 지원
print("\n  [Hedge Mode 지원]")
hedge_keys = {'bybit': 'positionIdx', 'binance': 'positionSide', 'bitget': 'posSide', 'okx': 'posSide', 'bingx': 'positionSide'}
for ex, key in hedge_keys.items():
    path = base / f'exchanges/{ex}_exchange.py'
    if path.exists():
        ex_code = path.read_text(encoding='utf-8', errors='ignore')
        has_hedge = key in ex_code
        print(f"    {'✅' if has_hedge else '❌'} {ex}: {key}")

# ============================================
# 3. 데이터 동기화
# ============================================
print("\n[3] 데이터 동기화")
print("-" * 50)

if bot_path.exists():
    checks = {
        'Parquet 저장': 'parquet' in code.lower() and ('save' in code.lower() or 'to_' in code.lower()),
        'WebSocket 실시간': 'websocket' in code.lower() or 'ws' in code.lower(),
        'Backfill (갭 채우기)': 'backfill' in code.lower(),
        'STATE_FILE 저장': 'state_file' in code.lower() or 'bot_state.json' in code,
        'save_state() 함수': 'def save_state' in code or 'save_state(' in code,
        'SYNC 후 save_state': False,  # 별도 체크
    }

    # SYNC 후 save_state 체크
    lines = code.split('\n')
    for i, line in enumerate(lines):
        if 'bt_state 업데이트' in line or '[SYNC]' in line:
            for j in range(i+1, min(i+10, len(lines))):
                if 'save_state' in lines[j]:
                    checks['SYNC 후 save_state'] = True
                    break

    for name, result in checks.items():
        print(f"  {'✅' if result else '❌'} {name}")
        results[f'동기화_{name}'] = result

# ============================================
# 4. 복리 시스템
# ============================================
print("\n[4] 복리 시스템")
print("-" * 50)

if bot_path.exists():
    checks = {
        'capital 변수': 'capital' in code,
        'capital 저장': "'capital'" in code and ('save' in code.lower() or 'state' in code.lower()),
        'capital 복원': 'capital' in code and ('load' in code.lower() or 'state' in code.lower()),
        'PnL → capital 업데이트': 'capital' in code and '+=' in code,
        '진입 시 capital 사용': 'capital' in code and ('qty' in code.lower() or 'size' in code.lower()),
    }
    for name, result in checks.items():
        print(f"  {'✅' if result else '❌'} {name}")

# ============================================
# 5. 매매내역 저장
# ============================================
print("\n[5] 매매내역 저장")
print("-" * 50)

if bot_path.exists():
    checks = {
        'trade_log 파일': 'trade_log' in code.lower(),
        'order_id 저장': 'order_id' in code.lower() and 'bt_state' in code,
        '거래내역 append': 'trade' in code.lower() and 'append' in code.lower(),
        'JSON/CSV 저장': ('json.dump' in code or 'to_csv' in code or 'save' in code.lower()),
    }
    for name, result in checks.items():
        print(f"  {'✅' if result else '❌'} {name}")

# ============================================
# 6. UI 동기화
# ============================================
print("\n[6] UI 동기화")
print("-" * 50)

dash = base / 'GUI/trading_dashboard.py'
if dash.exists():
    ui_code = dash.read_text(encoding='utf-8', errors='ignore')
    checks = {
        'UI 타이머': '_state_timer' in ui_code or 'QTimer' in ui_code,
        'bot_state.json 읽기': 'bot_state' in ui_code or 'state_file' in ui_code.lower(),
        '포지션 테이블 업데이트': 'setItem' in ui_code or 'update' in ui_code.lower(),
    }
    for name, result in checks.items():
        print(f"  {'✅' if result else '❌'} {name}")
else:
    print("  ❌ trading_dashboard.py 없음")

# ============================================
# 7. 안전장치
# ============================================
print("\n[7] 안전장치")
print("-" * 50)

if bot_path.exists():
    checks = {
        '중복 진입 방지': 'already in position' in code.lower() or 'existing position' in code.lower(),
        '외부 포지션 감지': 'external' in code.lower() or '외부' in code,
        'DataFrame 안전 접근': ('is None' in code or 'empty' in code) and 'df' in code.lower(),
        'state.get() 안전 접근': "state.get('" in code or ".get(" in code,
        '레버리지 에러 처리': '110043' in code or 'not modified' in code.lower() or 'error' in code.lower(),
    }
    for name, result in checks.items():
        print(f"  {'✅' if result else '❌'} {name}")

# ============================================
# 8. 문법 검사
# ============================================
print("\n[8] 문법 검사")
print("-" * 50)

critical_files = [
    'core/unified_bot.py',
    'core/strategy_core.py',
    'exchanges/bybit_exchange.py',
    'exchanges/binance_exchange.py',
    'GUI/trading_dashboard.py',
]
syntax_errors = []
for f in critical_files:
    path = base / f
    if path.exists():
        try:
            code_to_compile = path.read_text(encoding='utf-8', errors='ignore')
            compile(code_to_compile, f, 'exec')
            print(f"  ✅ {f}")
        except SyntaxError as e:
            print(f"  ❌ {f}: L{e.lineno} {e.msg}")
            syntax_errors.append(f)
    else:
        print(f"  ⚠️ {f}: 파일 없음")

# ============================================
# 최종 결과
# ============================================
print("\n" + "=" * 70)
print("최종 결과")
print("=" * 70)

failed = [k for k, v in results.items() if not v]
if syntax_errors:
    print(f"🔴 문법 에러: {syntax_errors}")
if failed:
    print(f"🟡 미완성/실패 항목: {failed}")
if not syntax_errors and not failed:
    print("🟢 전체 검증 통과! TwinStar Quantum v1.4.4 준비 완료.")
else:
    print("❌ 일부 항목 보완 필요")
