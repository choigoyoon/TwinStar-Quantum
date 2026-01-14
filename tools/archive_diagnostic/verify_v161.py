"""v1.6.1 시드 관리 기능 검증"""
from pathlib import Path
import logging

# 로깅 비활성화 (검증 출력만 보기 위함)
logging.getLogger().setLevel(logging.CRITICAL)

base = Path(__file__).parent
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 v1.6.1 시드 관리 기능 검증")
print("=" * 70)

if not bot.exists():
    print("❌ unified_bot.py 없음")
    exit()

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

checks = []

# 1) adjust_capital 함수
print("\n[1] adjust_capital 함수")
print("-" * 50)

for i, line in enumerate(lines, 1):
    if 'def adjust_capital' in line:
        print(f"  ✅ L{i}: {line.strip()}")
        checks.append("adjust_capital")
        # 함수 내용 일부
        for j in range(i, min(i+10, len(lines))):
            if lines[j].strip():
                print(f"     L{j+1}: {lines[j].strip()[:60]}")

# 2) reset_session 함수
print("\n[2] reset_session 함수")
print("-" * 50)

for i, line in enumerate(lines, 1):
    if 'def reset_session' in line:
        print(f"  ✅ L{i}: {line.strip()}")
        checks.append("reset_session")
        for j in range(i, min(i+10, len(lines))):
            if lines[j].strip():
                print(f"     L{j+1}: {lines[j].strip()[:60]}")

# 3) TradeStorage.reset_history
print("\n[3] TradeStorage 초기화")
print("-" * 50)

storage = base / 'storage' / 'trade_storage.py'
if storage.exists():
    s_code = storage.read_text(encoding='utf-8')
    for i, line in enumerate(s_code.split('\n'), 1):
        if 'def reset' in line or 'backup' in line.lower():
            if 'logging' not in line:
                print(f"  L{i}: {line.strip()[:60]}")
                checks.append("trade_storage_reset")

# 4) GUI 버튼 연동
print("\n[4] GUI 버튼 (±, ↺)")
print("-" * 50)

for gf in (base / 'GUI').glob('*.py'):
    try:
        g_code = gf.read_text(encoding='utf-8')
        if 'adjust' in g_code.lower() or 'reset' in g_code.lower():
            for i, line in enumerate(g_code.split('\n'), 1):
                if ('±' in line or '+/-' in line or 'adjust' in line.lower() or '↺' in line or 'reset' in line.lower()):
                    if 'button' in line.lower() or 'clicked' in line.lower() or 'connect' in line.lower():
                        if '#' not in line.strip()[:1]: # 주석 제외
                            print(f"  {gf.name} L{i}: {line.strip()[:55]}")
                            checks.append("gui_buttons")
    except Exception:

        pass

# 5) 상태 저장
print("\n[5] dashboard_state.json 저장")
print("-" * 50)

for gf in (base / 'GUI').glob('*.py'):
    try:
        g_code = gf.read_text(encoding='utf-8')
        if 'dashboard_state' in g_code:
            print(f"  ✅ {gf.name}에서 dashboard_state 사용")
            checks.append("state_save")
            break
    except Exception:

        pass

# 최종 결과
print("\n" + "=" * 70)
print("📊 v1.6.1 검증 결과")
print("=" * 70)

required = ['adjust_capital', 'reset_session']
for req in required:
    if req in checks:
        print(f"  ✅ {req}")
    else:
        print(f"  ❌ {req} 없음")

print(f"\n총 확인: {len(set(checks))}개 기능")

if all(req in checks for req in required):
    print("\n🎉 v1.6.1 시드 관리 기능 완료!")
    print("\n📦 빌드:")
    print("  cd C:\\매매전략")
    print("  pyinstaller staru_clean.spec --noconfirm")
else:
    print("\n⚠️ 오류 수정 후 재검증 필요")

print("\n결과 공유해줘")
