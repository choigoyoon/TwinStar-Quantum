from pathlib import Path

base = Path(r'C:\매매전략')

print("=" * 60)
print("백테스트 기반 리스크 한도 구현 준비")
print("=" * 60)

# 1. 백테스트 결과에서 MDD, 연패 추출 위치
print("\n[1] 백테스트 결과 저장 위치:")
for f in base.rglob('*.py'):
    if '__pycache__' in str(f):
        continue
    try:
        code = f.read_text(encoding='utf-8', errors='ignore')
        if 'mdd' in code.lower() or 'max_drawdown' in code.lower():
            if 'backtest' in str(f).lower() or 'result' in code.lower():
                print(f"  {f.name}: MDD 계산 있음")
        if 'losing_streak' in code.lower() or 'consecutive' in code.lower():
            print(f"  {f.name}: 연패 계산 있음")
    except Exception:

        pass

# 2. 현재 리스크 매니저 구조
print("\n[2] 리스크 매니저 연동 포인트:")
dash = base / 'GUI/trading_dashboard.py'
if dash.exists():
    code = dash.read_text(encoding='utf-8', errors='ignore')
    if 'circuit' in code.lower() or 'emergency' in code.lower():
        print("  ✅ 서킷브레이커 있음 - 여기에 연동")
    if 'risk' in code.lower():
        print("  ✅ 리스크 헤더 있음 - 여기에 표시")

# 3. 실시간 매매 기록
print("\n[3] 실시간 연패 추적:")
bot = base / 'core/unified_bot.py'
code = bot.read_text(encoding='utf-8', errors='ignore')
if 'trade_history' in code.lower() or 'trade_log' in code.lower():
    print("  ✅ 거래 기록 있음")
if 'win' in code.lower() and 'loss' in code.lower():
    print("  ✅ 승/패 구분 있음")

print("\n→ 결과 공유 후 구현")
