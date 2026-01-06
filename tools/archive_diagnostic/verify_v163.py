"""v1.6.3 복리 잔액 UI 구현 검증"""
from pathlib import Path

base = Path(r'C:\매매전략')
dashboard = base / 'GUI' / 'trading_dashboard.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 60)
print("🔍 v1.6.3 복리 잔액 UI 검증")
print("=" * 60)

if not dashboard.exists():
    print("❌ trading_dashboard.py 없음")
    exit()

code = dashboard.read_text(encoding='utf-8')
lines = code.split('\n')

# [1] 새로운 위젯 확인
print("\n[1] 📦 새로운 위젯 존재 여부")
widgets = {
    'current_label': False,
    'pnl_label': False,
    'lock_btn': False,
    'arrow_label': False,
}

for line in lines:
    for w in widgets:
        if f'self.{w}' in line and '=' in line:
            widgets[w] = True

for w, exists in widgets.items():
    print(f"  {'✅' if exists else '❌'} self.{w}")

# [2] 잠금 토글 메서드
print("\n[2] 🔒 _toggle_lock 메서드")
toggle_lock = []
in_toggle = False
for i, line in enumerate(lines, 1):
    if 'def _toggle_lock' in line:
        in_toggle = True
    if in_toggle:
        toggle_lock.append(f"  L{i}: {line.rstrip()[:60]}")
        if len(toggle_lock) > 1 and line.strip() and not line.startswith(' '):
            break
        if len(toggle_lock) >= 15:
            break

if toggle_lock:
    print(f"✅ _toggle_lock 발견:")
    for x in toggle_lock[:12]: print(x)
else:
    print("❌ _toggle_lock 메서드 없음")

# [3] update_balance 메서드
print("\n[3] 💰 update_balance 메서드")
update_bal = []
in_update = False
for i, line in enumerate(lines, 1):
    if 'def update_balance' in line:
        in_update = True
    if in_update:
        update_bal.append(f"  L{i}: {line.rstrip()[:60]}")
        if len(update_bal) > 1 and line.strip() and not line.startswith(' '):
            break
        if len(update_bal) >= 20:
            break

if update_bal:
    print(f"✅ update_balance 발견:")
    for x in update_bal[:15]: print(x)
else:
    print("❌ update_balance 메서드 없음")

# [4] 색상 코딩 확인
print("\n[4] 🎨 수익률 색상 코딩")
color_code = []
for i, line in enumerate(lines, 1):
    if '#4CAF50' in line or '#FF5252' in line:
        if 'pnl' in line.lower() or 'current' in line.lower():
            color_code.append(f"  L{i}: {line.strip()[:60]}")

if color_code:
    print(f"✅ 색상 코딩 {len(color_code)}개:")
    for x in color_code[:6]: print(x)
else:
    print("⚠️ pnl/current 관련 색상 코딩 미발견")

# [5] _sync_position_states에서 update_balance 호출
print("\n[5] 🔄 _sync에서 잔액 업데이트 연동")
sync_balance = []
in_sync = False
for i, line in enumerate(lines, 1):
    if 'def _sync_position_states' in line:
        in_sync = True
    if in_sync:
        if 'update_balance' in line or 'current_capital' in line:
            sync_balance.append(f"  L{i}: {line.strip()[:60]}")
        if 'def ' in line and '_sync' not in line:
            break

if sync_balance:
    print(f"✅ 동기화 연동 {len(sync_balance)}개:")
    for x in sync_balance: print(x)
else:
    print("⚠️ _sync에서 update_balance 호출 미발견")

# [6] 봇 엔진 current_capital 확인
print("\n[6] 🤖 봇 엔진 current_capital")
if bot.exists():
    bot_code = bot.read_text(encoding='utf-8')
    cap_lines = []
    for i, line in enumerate(bot_code.split('\n'), 1):
        if 'current_capital' in line and '=' in line:
            cap_lines.append(f"  L{i}: {line.strip()[:60]}")
    
    print(f"current_capital 할당: {len(cap_lines)}개")
    for x in cap_lines[:8]: print(x)
else:
    print("❌ unified_bot.py 없음")

# [7] 최종 체크리스트
print("\n" + "=" * 60)
print("📋 v1.6.3 체크리스트")
print("=" * 60)

checks = {
    "current_label 위젯": widgets.get('current_label', False),
    "pnl_label 위젯": widgets.get('pnl_label', False),
    "lock_btn 위젯": widgets.get('lock_btn', False),
    "_toggle_lock 메서드": len(toggle_lock) > 0,
    "update_balance 메서드": len(update_bal) > 0,
    "색상 코딩": len(color_code) > 0,
    "동기화 연동": len(sync_balance) > 0,
}

passed = sum(checks.values())
total = len(checks)

for name, ok in checks.items():
    print(f"  {'✅' if ok else '❌'} {name}")

print(f"\n결과: {passed}/{total} 통과")

if passed == total:
    print("\n🎉 v1.6.3 UI 구현 완료!")
    print("\n빌드 명령:")
    print("  cd C:\\매매전략")
    print("  pyinstaller staru_clean.spec --noconfirm")
else:
    print(f"\n⚠️ {total - passed}개 항목 구현 필요")
