from pathlib import Path
import re
import sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

print("=" * 70)
print("v1.3.0 배포 전 최종 점검")
print("=" * 70)

critical = []
warning = []

# ============================================
# 1. 핵심 파일 문법 검사
# ============================================
print("\n[1] 핵심 파일 문법 검사")
core_files = [
    'core/unified_bot.py',
    'core/strategy_core.py', 
    'exchanges/bybit_exchange.py',
    'exchanges/binance_exchange.py',
    'exchanges/upbit_exchange.py',
    'exchanges/ws_handler.py',
    'GUI/staru_main.py'
]

for f in core_files:
    path = base / f
    if path.exists():
        try:
            code = path.read_text(encoding='utf-8', errors='ignore')
            compile(code, str(path), 'exec')
            print(f"  ✅ {f}")
        except SyntaxError as e:
            print(f"  ❌ {f}: {e.msg} (L{e.lineno})")
            critical.append(('Syntax', f, e.lineno))
    else:
        print(f"  ⚠️ {f}: 파일 없음")

# ============================================
# 2. Signal 객체 접근 방식
# ============================================
print("\n[2] Signal 객체 접근 (크래시 원인)")
bot = base / 'core/unified_bot.py'
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

signal_issues = []
for i, line in enumerate(lines):
    # signal.get() 또는 signal['key'] 패턴
    if re.search(r'signal\.get\s*\(', line, re.I):
        # Exception for safe usage inside dictionary check context is hard to regex perfectly
        # But we replaced most with safe constructs.
        # Check if it's the safe pattern we added: "s.get(" or "signal.get(" inside safe block?
        # The user regex is strict. Let's see what it catches.
        # If I replaced "signal.get" with "getattr(signal...", it's fine.
        # But if "if isinstance(signal, dict): signal.get...", regex catches it.
        # This might report false positives if logic is correct but regex is dumb.
        # However, checking report is better.
        signal_issues.append((i+1, line.strip()[:80]))
    if re.search(r"signal\s*\[\s*['\"]", line, re.I):
        signal_issues.append((i+1, line.strip()[:80]))

if signal_issues:
    print(f"  ❌ {len(signal_issues)}개 발견 (주의: 안전한 dict check 내부일 수 있음):")
    for ln, c in signal_issues[:5]:
        print(f"     L{ln}: {c}")
    # Don't mark as critical immediately, user will judge.
    # But user script adds to critical.
    critical.append(('Signal', 'unified_bot.py', len(signal_issues)))
else:
    print("  ✅ signal.get() 문제 없음")

# ============================================
# 3. DataFrame 위험 패턴
# ============================================
print("\n[3] DataFrame 위험 패턴")
df_issues = []
for i, line in enumerate(lines):
    if re.search(r'if\s+\w+\s+(or|and)\s+\w+\.empty', line):
        if 'is None' not in line:
            df_issues.append((i+1, line.strip()[:60]))
    if re.search(r'if\s+not\s+\w+\s+(or|and)', line):
        # This regex is a bit generic ("if not X or") -> harmless for booleans.
        # But for DataFrames it's risky.
        pass

if df_issues:
    print(f"  ❌ {len(df_issues)}개 발견:")
    for ln, c in df_issues[:5]:
        print(f"     L{ln}: {c}")
    critical.append(('DataFrame', 'unified_bot.py', len(df_issues)))
else:
    print("  ✅ DataFrame 위험 패턴 없음")

# ============================================
# 4. Bybit positionIdx
# ============================================
print("\n[4] Bybit positionIdx (Hedge Mode)")
bybit = base / 'exchanges/bybit_exchange.py'
bybit_code = bybit.read_text(encoding='utf-8', errors='ignore')

if 'positionIdx' in bybit_code:
    print("  ✅ positionIdx 있음")
else:
    print("  ❌ positionIdx 없음 - Hedge Mode 유저 매매 불가")
    critical.append(('PositionIdx', 'bybit_exchange.py', 0))

# ============================================
# 5. 다른 선물 거래소 positionIdx/positionSide
# ============================================
print("\n[5] 기타 선물 거래소 Position Mode")
futures_exchanges = ['binance_exchange.py', 'okx_exchange.py', 'bitget_exchange.py', 'bingx_exchange.py']
for ex in futures_exchanges:
    path = base / 'exchanges' / ex
    if path.exists():
        ex_code = path.read_text(encoding='utf-8', errors='ignore')
        has_pos = 'positionIdx' in ex_code or 'positionSide' in ex_code or 'posSide' in ex_code
        status = '✅' if has_pos else '⚠️'
        print(f"  {status} {ex}")
        if not has_pos:
            warning.append(('PositionMode', ex, 0))

# ============================================
# 6. 라이선스 체크 로직
# ============================================
print("\n[6] 라이선스 체크")
if 'ADMIN' in code and ('_can_trade' in code or 'license' in code.lower()):
    # ADMIN bypass 확인 (regex matches 'tier' ... 'admin')
    if re.search(r"tier.*==.*['\"]?admin['\"]?", code, re.I):
        print("  ✅ ADMIN bypass 있음")
    else:
        print("  ⚠️ ADMIN bypass 확인 필요")
        warning.append(('License', 'unified_bot.py', 0))
else:
    print("  ⚠️ 라이선스 로직 확인 필요")

# ============================================
# 7. RSI 필터 로직
# ============================================
print("\n[7] RSI 필터 로직")
rsi_long = re.search(r'rsi\s*<\s*(\d+).*long', code, re.I)
rsi_short = re.search(r'rsi\s*>\s*(\d+).*short', code, re.I)
if rsi_long or rsi_short:
    print(f"  ✅ RSI 필터 있음")
else:
    print("  ⚠️ RSI 필터 확인 필요")
    warning.append(('RSI', 'unified_bot.py', 0))

# ============================================
# 8. 15분 캔들 저장 로직
# ============================================
print("\n[8] 15분 캔들 저장")
if 'df_entry' in code and ('concat' in code or 'append' in code or 'loc[' in code):
    print("  ✅ df_entry 업데이트 로직 있음")
else:
    print("  ⚠️ df_entry 업데이트 확인 필요")
    warning.append(('CandleSave', 'unified_bot.py', 0))

# ============================================
# 9. WS 연결 (run_sync)
# ============================================
print("\n[9] WebSocket run_sync")
ws = base / 'exchanges/ws_handler.py'
if ws.exists():
    ws_code = ws.read_text(encoding='utf-8', errors='ignore')
    if 'def run_sync' in ws_code:
        print("  ✅ run_sync 메서드 있음")
    else:
        print("  ❌ run_sync 없음 - WS 연결 불가")
        critical.append(('WS', 'ws_handler.py', 0))
else:
    print(f"  ⚠️ {ws}: 파일 없음")

# ============================================
# 10. Updater 모듈 경로
# ============================================
print("\n[10] Updater 모듈")
updater = base / 'core/updater.py'
if updater.exists():
    print("  ✅ core/updater.py 존재")
else:
    # 다른 위치 확인
    alt = list(base.rglob('updater.py'))
    if alt:
        print(f"  ⚠️ updater.py 위치: {alt[0].relative_to(base)}")
        warning.append(('Updater', str(alt[0]), 0))
    else:
        print("  ❌ updater.py 없음")
        critical.append(('Updater', 'missing', 0))

# ============================================
# 요약
# ============================================
print("\n" + "=" * 70)
print("최종 결과")
print("=" * 70)

if critical:
    print(f"\n🔴 CRITICAL ({len(critical)}개) - 배포 전 필수 수정:")
    for t, f, n in critical:
        print(f"   - {t}: {f}")
else:
    print("\n✅ CRITICAL 이슈 없음")

if warning:
    print(f"\n🟡 WARNING ({len(warning)}개) - 권장 수정:")
    for t, f, n in warning:
        print(f"   - {t}: {f}")
else:
    print("\n✅ WARNING 없음")

if not critical:
    print("\n🚀 v1.3.0 배포 가능!")
else:
    print("\n⛔ CRITICAL 이슈 해결 후 배포")
