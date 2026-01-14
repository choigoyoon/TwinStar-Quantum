"""v1.5.10 PnL 수정 최종 검증"""
from pathlib import Path

base = Path(__file__).parent
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 v1.5.10 PnL 수정 최종 검증")
print("=" * 70)

if not bot.exists():
    print("❌ unified_bot.py 없음")
    exit()

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

checks = {
    'size_based': False,
    'no_sign_flip': True,
    'position_side': False,
    'fee_deduct': False,
}

# 1) 수량 기반 계산
print("\n[1] 수량 기반 PnL 계산")
print("-" * 50)

for i, line in enumerate(lines, 1):
    lower = line.lower()
    if 'pnl_usd' in lower and 'size' in lower and '*' in line:
        print(f"  ✅ L{i}: {line.strip()[:70]}")
        checks['size_based'] = True
    elif 'pnl_usd' in lower and 'qty' in lower and '*' in line:
        print(f"  ✅ L{i}: {line.strip()[:70]}")
        checks['size_based'] = True
    elif 'profit_usd' in lower and 'size' in lower and '*' in line:
        print(f"  ✅ L{i}: {line.strip()[:70]}")
        checks['size_based'] = True

# 2) 부호 반전 제거 확인
print("\n[2] 부호 반전 로직 제거")
print("-" * 50)

for i, line in enumerate(lines, 1):
    if 'pnl_usd' in line and '= -' in line and 'pnl_usd' in line[line.find('= -'):]:
        print(f"  🔴 L{i}: {line.strip()[:70]}")
        checks['no_sign_flip'] = False
    if 'pnl_usd *= -1' in line.replace(' ', ''):
        print(f"  🔴 L{i}: {line.strip()[:70]}")
        checks['no_sign_flip'] = False

if checks['no_sign_flip']:
    print("  ✅ 부호 반전 로직 없음")

# 3) position.side 사용
print("\n[3] position.side 기반 방향")
print("-" * 50)

for i, line in enumerate(lines, 1):
    if 'self.position.side' in line or "position.side" in line:
        if ('pnl_pct' in line or 'pnl_usd' in line or 'profit_usd' in line) and ('==' in line or 'if' in line):
            print(f"  ✅ L{i}: {line.strip()[:70]}")
            checks['position_side'] = True

# 4) 수수료 차감
print("\n[4] 수수료 차감")
print("-" * 50)

for i, line in enumerate(lines, 1):
    lower = line.lower()
    if 'fee' in lower and ('pnl' in lower or 'profit' in lower):
        if '-' in line and ('total_fee' in line or 'fee' in line):
            print(f"  ✅ L{i}: {line.strip()[:70]}")
            checks['fee_deduct'] = True

# 최종 결과
print("\n" + "=" * 70)
print("📊 검증 결과")
print("=" * 70)

all_pass = True
for check, passed in checks.items():
    status = "✅" if passed else "❌"
    print(f"  {status} {check}")
    if not passed:
        all_pass = False

if all_pass:
    print("\n🎉 v1.5.10 PnL 수정 완료!")
    print("\n빌드 진행:")
    print("  cd C:\\매매전략")
    print("  pyinstaller staru_clean.spec --noconfirm")
else:
    print("\n⚠️ 일부 항목 확인 필요")

print("\n결과 공유해줘")
