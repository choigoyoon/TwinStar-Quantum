"""최종 통합 검증 + 빌드 준비"""
from pathlib import Path
import re
import os

base = Path(r'C:\매매전략')

print("=" * 70)
print("🔬 최종 통합 검증")
print("=" * 70)

errors = []
passes = []

# 1) 핵심 파일 문법 검사
print("\n[1] 문법 검사")
print("-" * 50)
core_files = [
    'core/unified_bot.py',
    'core/strategy_core.py', 
    'core/multi_sniper.py',
    'GUI/staru_main.py',
]

for f in core_files:
    fp = base / f
    if fp.exists():
        try:
            import py_compile
            py_compile.compile(str(fp), doraise=True)
            print(f"  ✅ {f}")
            passes.append(f"{f} 문법 ✅")
        except Exception as e:
            print(f"  ❌ {f}: {e}")
            errors.append(f"{f} 문법 오류")
    else:
        print(f"  ⚠️ {f} 없음")

# 2) 중복 계산 최종 확인
print("\n[2] 중복 계산 최종 확인")
print("-" * 50)

check_files = ['core/unified_bot.py', 'core/multi_sniper.py']
# 패턴 정의 (import 제외)
dup_patterns = [
    (r'ta\.rsi\s*\(', 'RSI'),
    (r'ta\.atr\s*\(', 'ATR'),
    (r'\.ewm\s*\(', 'EMA/MACD')
]

for f in check_files:
    fp = base / f
    if fp.exists():
        code = fp.read_text(encoding='utf-8')
        lines = code.split('\n')
        found_lines = []
        for i, line in enumerate(lines, 1):
            if 'import' in line.lower() or line.strip().startswith('#'):
                continue
            if 'self.strategy' in line or 'AlphaX7Core' in line:
                continue
                
            for p, name in dup_patterns:
                if re.search(p, line, re.IGNORECASE):
                    found_lines.append(f"  L{i}: {name} - {line.strip()[:50]}")
        
        if found_lines:
            print(f"  ⚠️ {f}: {len(found_lines)}개 직접계산 발견")
            for fl in found_lines[:3]:
                print(fl)
            errors.append(f"{f} 중복계산")
        else:
            print(f"  ✅ {f}: 중복 없음")
            passes.append(f"{f} 중복제거 ✅")

# 3) strategy_core 연결 확인
print("\n[3] Core 연결 확인")
print("-" * 50)
bot = base / 'core' / 'unified_bot.py'
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    if 'self.strategy' in code or 'AlphaX7' in code:
        print("  ✅ unified_bot → strategy_core 연결됨")
        passes.append("Core 연결 ✅")
    else:
        print("  ❌ Core 연결 없음")
        errors.append("Core 연결 없음")

sniper = base / 'core' / 'multi_sniper.py'
if sniper.exists():
    code = sniper.read_text(encoding='utf-8')
    # strategy 인스턴스 사용 및 manage_position_realtime 호출 확인
    if ('self.strategy' in code or 'AlphaX7' in code) and 'manage_position_realtime' in code:
        print("  ✅ multi_sniper → strategy_core 연결됨")
        passes.append("Sniper 연결 ✅")
    else:
        print("  ❌ multi_sniper Core 연결 미확인")
        errors.append("Sniper 연결 미확인")

# 4) spec 파일 확인
print("\n[4] 빌드 설정 확인")
print("-" * 50)
spec = base / 'staru_clean.spec'
if spec.exists():
    print(f"  ✅ {spec.name} 존재")
    passes.append("spec 파일 ✅")
else:
    print("  ❌ staru_clean.spec 없음")
    errors.append("spec 파일 없음")

# 최종 결과
print("\n" + "=" * 70)
print("📊 최종 검증 결과")
print("=" * 70)

print(f"\n✅ 통과: {len(passes)}개")
for p in passes:
    print(f"  - {p}")

if errors:
    print(f"\n❌ 오류: {len(errors)}개")
    for e in errors:
        print(f"  - {e}")
    print("\n⚠️ 오류 수정 후 빌드 진행")
else:
    print("\n" + "=" * 70)
    print("🎉 모든 검증 통과!")
    print("=" * 70)
    print("""
📦 빌드 명령:

  cd C:\\매매전략
  pyinstaller staru_clean.spec --noconfirm

📁 결과 위치:
  dist\\TwinStar_Quantum\\TwinStar_Quantum.exe

✅ 빌드 후 체크:
  □ EXE 실행 정상
  □ 거래소 연결 OK  
  □ 백테스트 실행 OK
  □ 로그에 에러 없음
""")

print("\n결과 공유해줘")
