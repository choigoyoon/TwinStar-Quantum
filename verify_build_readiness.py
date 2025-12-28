
from pathlib import Path
import ast
import json
import sys
import os

base = Path(r'C:\매매전략')

print("=" * 60)
print("v1.2.3 빌드 전 최종 통합 검증")
print("=" * 60)

errors = []
warnings = []

# ============================================
# 1. 문법 검증 (수정된 파일들)
# ============================================
print("\n[1] 문법 검증")

modified_files = [
    'exchanges/ws_handler.py',
    'exchanges/binance_exchange.py',
    'exchanges/upbit_exchange.py',
    'exchanges/bithumb_exchange.py',
    'exchanges/okx_exchange.py',
    'exchanges/bitget_exchange.py',
    'exchanges/bingx_exchange.py',
    'core/unified_bot.py',
]

for rel in modified_files:
    fpath = base / rel
    if not fpath.exists():
        print(f"  ⚠️ {rel}: 파일 없음")
        continue
    
    try:
        code = fpath.read_text(encoding='utf-8')
        ast.parse(code)
        print(f"  ✅ {rel}")
    except SyntaxError as e:
        print(f"  ❌ {rel}: L{e.lineno} {e.msg}")
        errors.append(f"{rel} 문법 에러")

# ============================================
# 2. WS 구현 확인
# ============================================
print("\n[2] WS 구현 상태")

exchanges = ['bybit', 'binance', 'upbit', 'bithumb', 'okx', 'bitget', 'bingx']
for ex in exchanges:
    fpath = base / 'exchanges' / f'{ex}_exchange.py'
    if fpath.exists():
        code = fpath.read_text(encoding='utf-8')
        has_ws = 'def start_websocket' in code
        has_handler = 'WSHandler' in code or 'ws_handler' in code.lower()
        
        if has_ws and has_handler:
            print(f"  ✅ {ex}: WS 완전 구현")
        elif has_ws:
            print(f"  ⚠️ {ex}: WS 메서드만 있음")
            warnings.append(f"{ex} WSHandler 연결 확인")
        else:
            print(f"  ❌ {ex}: WS 미구현")
            errors.append(f"{ex} WS 없음")

# ============================================
# 3. 시간 동기화 확인
# ============================================
print("\n[3] 시간 동기화")

for ex in exchanges:
    fpath = base / 'exchanges' / f'{ex}_exchange.py'
    if fpath.exists():
        code = fpath.read_text(encoding='utf-8')
        has_fetch = 'fetchTime' in code
        has_sync = 'sync_time' in code
        
        status = '✅' if (has_fetch or has_sync) else '❌'
        print(f"  {status} {ex}: fetchTime={'✅' if has_fetch else '❌'} sync={'✅' if has_sync else '❌'}")

# ============================================
# 4. 진입 흐름 확인
# ============================================
print("\n[4] 진입 흐름 (unified_bot.py)")

bot_path = base / 'core' / 'unified_bot.py'
if bot_path.exists():
    code = bot_path.read_text(encoding='utf-8')

    checks = {
        '_on_candle_close': '_on_candle_close' in code,
        '_process_new_candle': '_process_new_candle' in code,
        '_continue_backtest': '_continue_backtest' in code,
        '_execute_live_entry': '_execute_live_entry' in code,
        'execute_entry': 'def execute_entry' in code,
        'pending_signals maxlen': 'maxlen' in code and 'pending_signals' in code,
    }

    for check, result in checks.items():
        status = '✅' if result else '❌'
        print(f"  {status} {check}")
        if not result:
            errors.append(f"unified_bot: {check} 없음")
else:
    print("  ❌ unified_bot.py 없음")
    errors.append("unified_bot.py 없음")

# ============================================
# 5. version.json 확인
# ============================================
print("\n[5] version.json")

ver_file = base / 'version.json'
if ver_file.exists():
    try:
        v = json.loads(ver_file.read_text(encoding='utf-8'))
        print(f"  버전: {v.get('version')}")
        print(f"  download_url: {'✅' if v.get('download_url') else '❌'}")
    except Exception as e:
        print(f"  ❌ version.json 파싱 실패: {e}")
        errors.append("version.json 파싱 실패")
else:
    print("  ❌ version.json 없음")
    errors.append("version.json 없음")

# ============================================
# 6. Import 테스트
# ============================================
print("\n[6] Import 테스트")

sys.path.insert(0, str(base))
os.chdir(str(base))

test_imports = [
    ('ws_handler', 'from exchanges.ws_handler import WebSocketHandler'), # Fixed import name
    ('unified_bot', 'from core.unified_bot import UnifiedBot'),
    ('strategy_core', 'from core.strategy_core import AlphaX7Core'),
]

for name, stmt in test_imports:
    try:
        exec(stmt)
        print(f"  ✅ {name}")
    except Exception as e:
        print(f"  ❌ {name}: {str(e)[:100]}")
        errors.append(f"Import 실패: {name}")

# ============================================
# 결과
# ============================================
print("\n" + "=" * 60)
print("최종 검증 결과")
print("=" * 60)

print(f"❌ 에러: {len(errors)}개")
print(f"⚠️ 경고: {len(warnings)}개")

if errors:
    print("\n[에러 목록]")
    for e in errors:
        print(f"  - {e}")

if warnings:
    print("\n[경고 목록]")
    for w in warnings:
        print(f"  - {w}")

if not errors:
    print("\n✅ 빌드 가능!")
    print("\n빌드 명령어:")
    print("  cd C:\\매매전략")
    print("  pyinstaller staru_clean.spec --noconfirm")
else:
    print("\n❌ 에러 수정 후 빌드")
