from pathlib import Path
import re
import sys
import json

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print("=" * 70)
print("v1.3.0 배포 전 최종 점검")
print("=" * 70)

critical = []
warning = []

# 1. 핵심 파일 문법 검사
print("\n[1] 핵심 파일 문법 검사")
core_files = [
    'core/unified_bot.py',
    'core/strategy_core.py', 
    'core/updater.py',
    'exchanges/bybit_exchange.py',
    'exchanges/binance_exchange.py',
    'exchanges/ws_handler.py',
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
        warning.append(('Missing', f, 0))

# 2. Signal 객체 접근
print("\n[2] Signal.get() 크래시 패턴")
bot = base / 'core/unified_bot.py'
code = bot.read_text(encoding='utf-8', errors='ignore')
lines = code.split('\n')

signal_issues = []
for i, line in enumerate(lines):
    if re.search(r'signal\.get\s*\(', line, re.I):
        # Naive filtering: if 'getattr' is on the line, ignore.
        # This will flag `signal.get(...)` even if correctly used for dict.
        # We'll just report what logic requests.
        if 'getattr' not in line and '#' not in line.split('signal')[0]:
            signal_issues.append((i+1, line.strip()[:60]))

if signal_issues:
    print(f"  ❌ {len(signal_issues)}개 (False Positive 가능성 있음):")
    for ln, c in signal_issues[:3]:
        print(f"     L{ln}: {c}")
    # We add to critical but will evaluate output manually
    critical.append(('Signal', 'unified_bot.py', len(signal_issues)))
else:
    print("  ✅ 없음")

# 3. DataFrame 위험 패턴
print("\n[3] DataFrame 위험 패턴")
df_issues = []
for i, line in enumerate(lines):
    if re.search(r'if\s+\w+\s+or\s+\w+\.empty', line) and 'is None' not in line:
        df_issues.append((i+1, line.strip()[:60]))

if df_issues:
    print(f"  ❌ {len(df_issues)}개")
    critical.append(('DataFrame', 'unified_bot.py', len(df_issues)))
else:
    print("  ✅ 없음")

# 4. positionIdx/positionSide
print("\n[4] 선물 거래소 Position Mode")
exchanges = {
    'bybit_exchange.py': 'positionIdx',
    'binance_exchange.py': 'positionSide',
    'bitget_exchange.py': 'posSide',
    'bingx_exchange.py': 'positionSide',
    'okx_exchange.py': 'posSide',
}

for ex, keyword in exchanges.items():
    path = base / 'exchanges' / ex
    if path.exists():
        ex_code = path.read_text(encoding='utf-8', errors='ignore')
        if keyword in ex_code:
            print(f"  ✅ {ex}: {keyword}")
        else:
            print(f"  ❌ {ex}: {keyword} 없음")
            # Special case: OKX uses 'posSide' but user map checked 'posSide'.
            # If failed, it's real.
            critical.append(('Position', ex, 0))
    else:
        print(f"  ⚠️ {ex}: 파일 없음")

# 5. WS run_sync
print("\n[5] WebSocket run_sync")
ws = base / 'exchanges/ws_handler.py'
if ws.exists():
    ws_code = ws.read_text(encoding='utf-8', errors='ignore')
    if 'def run_sync' in ws_code:
        print("  ✅ run_sync 있음")
    else:
        print("  ❌ run_sync 없음")
        critical.append(('WS', 'ws_handler.py', 0))
else:
    print("  ❌ ws_handler.py 없음")

# 6. version.json
print("\n[6] version.json")
ver_file = base / 'version.json'
if ver_file.exists():
    try:
        ver = json.loads(ver_file.read_text(encoding='utf-8'))
        print(f"  버전: {ver.get('version', '?')}")
        if ver.get('version') != '1.3.0':
            warning.append(('Version', 'version.json', 0))
    except Exception as e:
        print(f"  ❌ JSON 파싱 실패: {e}")
        critical.append(('JSON', 'version.json', 0))

# 결과
print("\n" + "=" * 70)
if critical:
    print(f"🔴 CRITICAL: {len(critical)}개")
    for t, f, n in critical:
        print(f"   - {t}: {f}")
    print("\n⛔ 수정 후 배포")
else:
    print("✅ CRITICAL 없음")
    
if warning:
    print(f"🟡 WARNING: {len(warning)}개")
    
if not critical:
    print("\n🚀 v1.3.0 배포 가능!")
    print("\ncd C:\\매매전략")
    print("pyinstaller staru_clean.spec --noconfirm")
