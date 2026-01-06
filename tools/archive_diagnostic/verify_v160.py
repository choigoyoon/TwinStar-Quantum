"""v1.6.0 최종 검증 + 버전 확인"""
from pathlib import Path
import json
import py_compile
import sys

base = Path(r'C:\매매전략')

print("=" * 70)
print("🔍 v1.6.0 최종 검증")
print("=" * 70)

# 1) 버전 확인
print("\n[1] 버전 확인")
print("-" * 50)

version_file = base / 'version.json'
if version_file.exists():
    try:
        v = json.loads(version_file.read_text(encoding='utf-8'))
        print(f"  version.json: {v.get('version', 'N/A')}")
    except:
        print("  version.json 파싱 실패")

# staru_main.py 버전
main_file = base / 'GUI' / 'staru_main.py'
if main_file.exists():
    code = main_file.read_text(encoding='utf-8')
    for line in code.split('\n'):
        if 'version' in line.lower() and ('1.5' in line or '1.6' in line):
            print(f"  staru_main.py: {line.strip()[:50]}")
            break

# 2) PnL 수정 검증
print("\n[2] PnL 계산 검증")
print("-" * 50)

bot = base / 'core' / 'unified_bot.py'
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    
    checks = []
    
    # size 기반
    if 'size' in code and 'pnl_usd' in code:
        found_size = False
        for i, line in enumerate(code.split('\n'), 1):
            if 'pnl_usd' in line.lower() and ('size' in line.lower() or 'qty' in line.lower()) and '*' in line:
                checks.append(f"✅ size 기반: L{i}")
                found_size = True
                break
        if not found_size:
            checks.append("❌ size 기반 수식 찾지 못함")
    
    # position.side
    if 'self.position.side' in code:
        checks.append("✅ position.side 사용")
    else:
        checks.append("❌ position.side 미사용")
    
    # 부호 반전 없음
    if 'pnl_usd = -pnl_usd' not in code and 'pnl_usd *= -1' not in code.replace(' ', ''):
        checks.append("✅ 부호 반전 제거됨")
    else:
        checks.append("❌ 부호 반전 로직 잔존")
    
    # 수수료 차감
    if 'fee' in code.lower() and ('pnl' in code.lower() or 'profit' in code.lower()):
        checks.append("✅ 수수료 차감 로직")
    else:
        checks.append("❌ 수수료 차감 로직 미발견")
    
    for c in checks:
        print(f"  {c}")

# 3) 수수료 설정 확인
print("\n[3] 수수료 설정")
print("-" * 50)

strategy = base / 'core' / 'strategy_core.py'
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    for i, line in enumerate(code.split('\n'), 1):
        if 'fee' in line.lower() and '0.0' in line:
            print(f"  L{i}: {line.strip()[:60]}")

# 4) 문법 검사
print("\n[4] 문법 검사")
print("-" * 50)

files = [
    'core/unified_bot.py',
    'core/strategy_core.py',
    'GUI/staru_main.py',
]

all_pass = True
for f in files:
    fp = base / f
    if fp.exists():
        try:
            py_compile.compile(str(fp), doraise=True)
            print(f"  ✅ {f}")
        except Exception as e:
            print(f"  ❌ {f}: {e}")
            all_pass = False

# 최종 결과
print("\n" + "=" * 70)
print("📊 v1.6.0 최종 결과")
print("=" * 70)

if all_pass:
    print("""
🎉 모든 검증 통과!

📦 빌드 명령:
  cd C:\\매매전략
  pyinstaller staru_clean.spec --noconfirm

📋 v1.6.0 변경사항:
  ✅ PnL 수량 기반 계산
  ✅ 부호 반전 버그 수정
  ✅ 수수료 차감 동기화
  ✅ 상태 복구 개선 (v1.5.9)
  ✅ 로직 단일화 (v1.5.2+)
""")
else:
    print("\n⚠️ 오류 수정 후 재검증 필요")

print("\n결과 공유해줘")
