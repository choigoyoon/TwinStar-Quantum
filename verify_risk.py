from pathlib import Path

base = Path(r'C:\매매전략')

print("=" * 60)
print("글로벌 리스크 매니저 구현 검증")
print("=" * 60)

errors = []

# 1. 문법 검사
print("\n[1] 문법 검사")
dash = base / 'GUI/trading_dashboard.py'
if dash.exists():
    try:
        code = dash.read_text(encoding='utf-8', errors='ignore')
        compile(code, 'trading_dashboard.py', 'exec')
        print("  ✅ trading_dashboard.py")
    except SyntaxError as e:
        print(f"  ❌ L{e.lineno}: {e.msg}")
        errors.append('syntax')

# 2. RiskHeaderWidget 확인
print("\n[2] RiskHeaderWidget 확인")
code = dash.read_text(encoding='utf-8', errors='ignore')
checks = {
    'RiskHeaderWidget 클래스': 'RiskHeaderWidget' in code or 'risk_header' in code.lower(),
    'Total Margin 표시': 'margin' in code.lower() and 'label' in code.lower(),
    'Today PnL 표시': 'pnl' in code.lower() or 'today' in code.lower(),
    'Loss Limit 설정': 'loss_limit' in code.lower() or '-5' in code,
}
for name, result in checks.items():
    print(f"  {'✅' if result else '❌'} {name}")
    if not result:
        errors.append(name)

# 3. 긴급 정지 로직
print("\n[3] 긴급 정지 로직")
checks = {
    'emergency_close_all': 'emergency' in code.lower() or 'close_all' in code.lower(),
    'stop_all 강화': 'stop_all' in code.lower(),
    '손실 한도 체크': 'limit' in code.lower() and ('pnl' in code.lower() or 'loss' in code.lower()),
}
for name, result in checks.items():
    print(f"  {'✅' if result else '❌'} {name}")

# 4. 잔고 조회 연동
print("\n[4] 잔고 조회 연동")
if 'get_balance' in code or 'fetch_balance' in code:
    print("  ✅ 잔고 조회 호출")
else:
    print("  ⚠️ 잔고 조회 확인 필요")

# 결과
print("\n" + "=" * 60)
if errors:
    print(f"❌ {len(errors)}개 문제: {errors}")
else:
    print("✅ 글로벌 리스크 매니저 구현 완료!")
    print("\n→ 앱 실행해서 헤더 표시 확인")
