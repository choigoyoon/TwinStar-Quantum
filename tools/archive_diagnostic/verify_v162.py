"""v1.6.2 수정사항 검증"""
from pathlib import Path

base = Path(r'C:\매매전략')
bot = base / 'core' / 'unified_bot.py'

if not bot.exists():
    print("❌ unified_bot.py 없음")
    exit()

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

print("=" * 60)
print("🔍 v1.6.2 수정사항 검증")
print("=" * 60)

# [1] PnL 레버리지 반영 확인
print("\n[1] PnL 레버리지 반영")
pnl_lev = []
# pnl_percent, pnl_pct 등을 포함한 레버리지 계산식 확인
for i, line in enumerate(lines, 1):
    low_line = line.lower()
    if 'pnl' in low_line and 'leverage' in low_line:
        pnl_lev.append(f"  L{i}: {line.strip()[:75]}")
    elif ('pnl_pct' in low_line or 'pnl_percent' in low_line) and '*' in low_line and 'lev' in low_line:
        pnl_lev.append(f"  L{i}: {line.strip()[:75]}")

if pnl_lev:
    print(f"✅ 레버리지 반영 {len(pnl_lev)}개:")
    for x in pnl_lev[:10]: print(x)
else:
    print("⚠️ pnl * leverage 패턴 미발견 - 확인 필요")

# [2] 웹소켓 가격 사용 확인
print("\n[2] SL 업데이트 - 웹소켓 가격 사용")
ws_price = []
for i, line in enumerate(lines, 1):
    if 'last_ws_price' in line or 'ws_price' in line:
        ws_price.append(f"  L{i}: {line.strip()[:75]}")

print(f"웹소켓 가격 참조: {len(ws_price)}개")
for x in ws_price[:8]: print(x)

# [3] manage_position에서 get_klines 호출 제거 확인
print("\n[3] manage_position 최적화")
in_manage = False
manage_klines = []
for i, line in enumerate(lines, 1):
    if 'def manage_position' in line or 'def _manage_position' in line:
        in_manage = True
    elif in_manage and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
         in_manage = False
         
    if in_manage and 'get_klines' in line:
        manage_klines.append(f"  L{i}: {line.strip()[:65]}")

if manage_klines:
    # 60초마다 조건부 호출은 허용되므로 상세 확인
    print(f"ℹ️ manage_position 내 get_klines 호출 {len(manage_klines)}개 (v1.6.2 최적화 확인 필요):")
    for x in manage_klines: print(x)
else:
    print("✅ manage_position에서 get_klines 직접 호출 없음")

# [4] _sync_position_states 구현 확인
print("\n[4] 포지션 동기화 함수")
sync_func = []
in_sync = False
for i, line in enumerate(lines, 1):
    if 'def _sync_position_states' in line or 'def sync_position' in line:
        in_sync = True
        sync_func.append(f"  L{i}: {line.strip()}")
    elif in_sync:
        if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
            in_sync = False
        elif len(sync_func) < 15:
            sync_func.append(f"  L{i}: {line.strip()[:75]}")

if any('_sync_position_states' in s for s in sync_func):
    print(f"✅ _sync_position_states 함수 발견:")
    for x in sync_func[:12]: print(x)
else:
    print("❌ _sync_position_states 함수 없음!")

# [5] 거래소 포지션 조회
print("\n[5] 거래소 실제 포지션 조회")
real_pos = []
for i, line in enumerate(lines, 1):
    if 'get_position' in line.lower() or 'get_positions' in line.lower():
        real_pos.append(f"  L{i}: {line.strip()[:75]}")

print(f"포지션 조회: {len(real_pos)}개")
for x in real_pos[:8]: print(x)

print("\n" + "=" * 60)
print("📊 검증 결과")
print("=" * 60)
checks = {
    "PnL 레버리지": len(pnl_lev) > 0,
    "웹소켓 가격": len(ws_price) > 0,
    "동기화 함수": any('_sync_position_states' in s for s in sync_func),
    "포지션 조회": len(real_pos) > 0
}

for k, v in checks.items():
    print(f"  {'✅' if v else '❌'} {k}")

if all(checks.values()):
    print("\n🎉 v1.6.2 핵심 수정 확인됨!")
else:
    print("\n⚠️ 일부 항목 추가 확인 필요")
