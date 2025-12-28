from pathlib import Path

base = Path(r'C:\매매전략')

print("=" * 60)
print("Equity Curve 구현 검증")
print("=" * 60)

errors = []

# 1. 문법 검사
print("\n[1] 문법 검사")
files = [
    'GUI/dashboard_widgets.py',
    'GUI/trading_dashboard.py',
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

# 2. EquityCurveWidget 클래스 확인
print("\n[2] EquityCurveWidget 확인")
widgets = base / 'GUI/dashboard_widgets.py'
if widgets.exists():
    code = widgets.read_text(encoding='utf-8', errors='ignore')
    checks = {
        'class EquityCurveWidget': 'class EquityCurveWidget' in code,
        'FigureCanvas': 'FigureCanvas' in code,
        'update_data': 'def update_data' in code,
        'cumulative': 'cumsum' in code or 'cumulative' in code.lower(),
    }
    for name, result in checks.items():
        print(f"  {'✅' if result else '❌'} {name}")
        if not result:
            errors.append(name)

# 3. 대시보드 연동 확인
print("\n[3] 대시보드 연동")
dash = base / 'GUI/trading_dashboard.py'
if dash.exists():
    code = dash.read_text(encoding='utf-8', errors='ignore')
    checks = {
        'EquityCurveWidget import': 'EquityCurveWidget' in code,
        'equity_curve 인스턴스': 'equity_curve' in code.lower(),
        'update_data 호출': 'update_data' in code,
    }
    for name, result in checks.items():
        print(f"  {'✅' if result else '❌'} {name}")
        if not result:
            errors.append(name)

# 4. matplotlib 백엔드 확인
print("\n[4] Matplotlib Qt5 백엔드")
for f in ['GUI/dashboard_widgets.py', 'GUI/trading_dashboard.py']:
    path = base / f
    if path.exists():
        code = path.read_text(encoding='utf-8', errors='ignore')
        if 'backend_qt5agg' in code.lower() or 'FigureCanvasQTAgg' in code:
            print(f"  ✅ {f}: Qt5 백엔드 사용")

# 결과
print("\n" + "=" * 60)
if errors:
    print(f"❌ {len(errors)}개 문제: {errors}")
else:
    print("✅ Equity Curve 구현 완료!")
    print("\n→ 앱 실행해서 그래프 표시 확인")
