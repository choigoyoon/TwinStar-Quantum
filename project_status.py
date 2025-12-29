from pathlib import Path
import json

base = Path(r'C:\매매전략')

print("=" * 70)
print("프로젝트 전체 상태 체크")
print("=" * 70)

# 1. 기본 구조
print("\n[1] 프로젝트 구조")
folders = ['core', 'exchanges', 'GUI', 'utils', 'data']
for f in folders:
    path = base / f
    if path.exists():
        py_files = len(list(path.glob('*.py')))
        print(f"  ✅ {f}/ ({py_files}개 .py)")
    else:
        print(f"  ❌ {f}/ 없음")

# 2. 버전 정보
print("\n[2] 버전 정보")
ver_file = base / 'version.json'
if ver_file.exists():
    ver = json.loads(ver_file.read_text())
    print(f"  버전: {ver.get('version', '?')}")
    print(f"  download_url: {'✅' if ver.get('download_url') else '❌'}")
else:
    print("  ❌ version.json 없음")

# 3. 핵심 파일 존재 + 문법
print("\n[3] 핵심 파일 문법 검사")
core_files = [
    'core/unified_bot.py',
    'core/strategy_core.py',
    'core/updater.py',
    'exchanges/bybit_exchange.py',
    'exchanges/binance_exchange.py',
    'exchanges/ws_handler.py',
    'GUI/staru_main.py',
]
for f in core_files:
    path = base / f
    if path.exists():
        try:
            code = path.read_text(encoding='utf-8', errors='ignore')
            compile(code, f, 'exec')
            lines = len(code.split('\n'))
            print(f"  ✅ {f} ({lines}줄)")
        except SyntaxError as e:
            print(f"  ❌ {f}: 문법오류 L{e.lineno}")
    else:
        print(f"  ⚠️ {f}: 없음")

# 4. 빌드 파일
print("\n[4] 빌드 설정")
spec = base / 'staru_clean.spec'
bat = base / 'build_clean_dist.bat'
print(f"  spec 파일: {'✅' if spec.exists() else '❌'}")
print(f"  빌드 스크립트: {'✅' if bat.exists() else '❌'}")

# 5. 최근 수정된 파일
print("\n[5] 최근 수정 파일 (24시간 내)")
import time
now = time.time()
recent = []
for f in base.rglob('*.py'):
    if '__pycache__' not in str(f):
        mtime = f.stat().st_mtime
        if now - mtime < 86400:
            recent.append((f.relative_to(base), mtime))

recent.sort(key=lambda x: -x[1])
for f, mt in recent[:10]:
    from datetime import datetime
    dt = datetime.fromtimestamp(mt).strftime('%H:%M')
    print(f"  {dt} - {f}")

# 6. 알려진 문제 패턴
print("\n[6] 알려진 문제 패턴 스캔")
issues = 0

# DataFrame 위험
bot = base / 'core/unified_bot.py'
if bot.exists():
    code = bot.read_text(encoding='utf-8', errors='ignore')
    import re
    df_danger = re.findall(r'getattr\([^)]+\)\s+or\s+self\.df', code)
    if df_danger:
        print(f"  ⚠️ DataFrame or 패턴: {len(df_danger)}개")
        issues += len(df_danger)
    
    signal_get = re.findall(r'signal\.get\(', code, re.I)
    if signal_get:
        print(f"  ⚠️ signal.get() 패턴: {len(signal_get)}개")
        issues += len(signal_get)

if issues == 0:
    print("  ✅ 알려진 문제 패턴 없음")

# 7. 거래소 Position Mode
print("\n[7] 거래소 Position Mode 지원")
exchanges = {
    'bybit_exchange.py': 'positionIdx',
    'binance_exchange.py': 'positionSide',
    'bitget_exchange.py': 'posSide',
    'okx_exchange.py': 'posSide',
    'bingx_exchange.py': 'positionSide',
}
for ex, keyword in exchanges.items():
    path = base / 'exchanges' / ex
    if path.exists():
        code = path.read_text(encoding='utf-8', errors='ignore')
        status = '✅' if keyword in code else '❌'
        print(f"  {status} {ex}: {keyword}")

print("\n" + "=" * 70)
print("요약")
print("=" * 70)
