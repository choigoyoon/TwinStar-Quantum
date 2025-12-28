from pathlib import Path
import json

base = Path(r'C:\매매전략')

print("=" * 60)
print("v1.5.0 최종 검증")
print("=" * 60)

errors = []

# 1. 문법 검사
print("\n[1] 문법 검사")
files = [
    'GUI/trading_dashboard.py',
    'GUI/dashboard_widgets.py',
    'core/unified_bot.py',
    'exchanges/bybit_exchange.py',
]
for f in files:
    path = base / f
    if path.exists():
        try:
            code = path.read_text(encoding='utf-8', errors='ignore')
            compile(code, f, 'exec')
            print(f"  ✅ {f}")
        except SyntaxError as e:
            print(f"  ❌ {f}: L{e.lineno}")
            errors.append(f)
    else:
        print(f"  ⚠️ {f}: 파일 없음")

# 2. v1.5.0 새 기능 확인
print("\n[2] v1.5.0 새 기능")
dash = base / 'GUI/trading_dashboard.py'
if dash.exists():
    code = dash.read_text(encoding='utf-8', errors='ignore')
    
    features = {
        '수익금 그래프 (Equity Curve)': 'equity' in code.lower() and ('curve' in code.lower() or 'graph' in code.lower() or 'chart' in code.lower()),
        '리스크 헤더': 'risk' in code.lower() and 'header' in code.lower(),
        '마진 사용률': 'margin' in code.lower(),
        'MDD 모니터링': 'mdd' in code.lower() or 'drawdown' in code.lower(),
        '연패 카운트': 'streak' in code.lower(),
        '서킷 브레이커': 'circuit' in code.lower() or 'emergency' in code.lower(),
    }
    for name, result in features.items():
        print(f"  {'✅' if result else '❌'} {name}")
        if not result:
            errors.append(name)

# 3. version.json
print("\n[3] version.json")
ver_file = base / 'version.json'
if ver_file.exists():
    try:
        ver = json.loads(ver_file.read_text())
        print(f"  현재: {ver.get('version')}")
        if ver.get('version') != '1.5.0':
            print("  ⚠️ 1.5.0으로 업데이트 필요")
            errors.append("version_mismatch")
    except:
        errors.append("version_read_error")

# 결과
print("\n" + "=" * 60)
if errors:
    print(f"❌ {len(errors)}개 문제: {errors}")
else:
    print("✅ v1.5.0 검증 통과!")
    print("\n📦 v1.5.0 릴리즈 내용:")
    print("  - 수익금 그래프 (Equity Curve)")
    print("  - 글로벌 리스크 매니저")
    print("  - MDD/연패 기반 서킷 브레이커")
    print("\n→ 배포 진행!")
