from pathlib import Path

base = Path(r'C:\매매전략')

print("=" * 60)
print("글로벌 리스크 매니저 구현 준비")
print("=" * 60)

# 1. 현재 마진/잔고 조회 기능 확인
print("\n[1] 잔고/마진 조회 기능:")
for ex in ['bybit', 'binance', 'okx', 'bitget']:
    path = base / f'exchanges/{ex}_exchange.py'
    if path.exists():
        code = path.read_text(encoding='utf-8', errors='ignore')
        has_balance = 'get_balance' in code or 'fetch_balance' in code
        has_margin = 'margin' in code.lower() or 'equity' in code.lower()
        print(f"  {ex}: 잔고{'✅' if has_balance else '❌'} | 마진{'✅' if has_margin else '❌'}")

# 2. 대시보드 헤더 영역 확인
print("\n[2] 대시보드 헤더:")
dash = base / 'GUI/trading_dashboard.py'
if dash.exists():
    code = dash.read_text(encoding='utf-8', errors='ignore')
    if 'header' in code.lower() or 'top' in code.lower():
        print("  ✅ 헤더 영역 있음")
    if 'Trading Control' in code:
        print("  ✅ Trading Control 섹션 있음")

# 3. 멀티봇 관리 구조
print("\n[3] 멀티봇 관리:")
if 'active_bots' in code or 'bot_list' in code.lower():
    print("  ✅ 봇 목록 관리 있음")
if 'stop_all' in code.lower():
    print("  ✅ 전체 정지 기능 있음")

print("\n→ 결과 공유 후 구현 방향 결정")
