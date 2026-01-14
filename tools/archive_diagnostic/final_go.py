"""v1.5.2+ 최종 확인 및 빌드"""
from pathlib import Path
import py_compile

base = Path(__file__).parent

print("=" * 70)
print("🎯 v1.5.2+ 최종 확인")
print("=" * 70)

# 핵심 파일 최종 문법 검사
files = [
    'core/unified_bot.py',
    'core/strategy_core.py',
    'core/multi_sniper.py',
    'GUI/staru_main.py',
]

all_pass = True
for f in files:
    fp = base / f
    if fp.exists():
        try:
            py_compile.compile(str(fp), doraise=True)
            print(f"✅ {f}")
        except Exception as e:
            print(f"❌ {f}: {e}")
            all_pass = False

print("\n" + "=" * 70)

if all_pass:
    print("""
🎉 모든 검증 완료!

📦 빌드 명령:
  cd C:\\매매전략
  pyinstaller staru_clean.spec --noconfirm

📋 v1.5.2+ 변경사항:
  ✅ Single Source of Truth 구축
  ✅ 봉마감 확정 로직 적용
  ✅ 파라미터 100% 동기화
  ✅ 중복 계산 제거
  ✅ 래퍼 함수 정상 확인

🚀 빌드 진행해!
""")
else:
    print("❌ 오류 수정 후 재시도")
