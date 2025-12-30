"""프로젝트 심층 검증 - 모든 연결고리 체크"""
from pathlib import Path
import re
import os

base = Path(r'C:\매매전략')

print("=" * 70)
print("🔬 TwinStar Quantum 심층 검증")
print("=" * 70)

errors = []
warnings = []
passes = []

# ============================================================
# [1] 계산 로직 Single Source of Truth
# ============================================================
print("\n" + "=" * 70)
print("[1] 계산 로직 Single Source of Truth")
print("=" * 70)

strategy = base / 'core' / 'strategy_core.py'
bot = base / 'core' / 'unified_bot.py'
sniper = base / 'core' / 'multi_sniper.py'

# strategy_core에 있어야 할 핵심 함수
required_in_core = [
    ('_extract_all_signals', '패턴 추출'),
    ('manage_position_realtime', 'Trailing Stop'),
    ('get_mtf_trend', '4H 트렌드'),
    ('detect_signal', '시그널 감지'),
    ('calculate_atr', 'ATR 계산'),
    ('calculate_rsi', 'RSI 계산'),
]

print("\n[1-1] strategy_core 핵심 함수 존재 여부")
print("-" * 50)
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    for func, desc in required_in_core:
        if f'def {func}' in code:
            print(f"  ✅ {func}: {desc}")
            passes.append(f"Core.{func}")
        else:
            print(f"  ❌ {func}: {desc} 없음")
            errors.append(f"Core.{func} 없음")

# unified_bot에서 중복 정의 체크 (완전한 중복 함수만)
print("\n[1-2] unified_bot 중복 함수 체크")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    duplicates = []
    # 봇 전용 래퍼 함수는 허용하되, 코어와 완벽히 이름이 겹치는 중복 정의만 체크
    for func, desc in required_in_core:
        # def func(...) 형태의 정의가 실매매 봇에 있는지 확인
        if re.search(rf'def\s+{func}\s*\(', code):
            duplicates.append(f"{func} (중복!)")
    
    if duplicates:
        print(f"  ⚠️ 중복 함수 발견: {duplicates}")
        warnings.append("Bot 중복 함수")
    else:
        print("  ✅ 중복 함수 없음")
        passes.append("Bot 중복 없음")

# ============================================================
# [2] 계산식 직접 호출 vs Core 위임
# ============================================================
print("\n" + "=" * 70)
print("[2] 직접 계산 vs Core 위임")
print("=" * 70)

direct_calc_patterns = {
    'RSI': r'ta\.rsi|talib\.RSI',
    'ATR': r'ta\.atr|talib\.ATR',
    'EMA': r'\.ewm\(|ta\.ema|talib\.EMA',
}

check_files = [
    ('core/unified_bot.py', '실매매 봇'),
    ('core/multi_sniper.py', '멀티 스나이퍼'),
]

for file_path, desc in check_files:
    fp = base / file_path
    if fp.exists():
        code = fp.read_text(encoding='utf-8')
        found = []
        for name, pattern in direct_calc_patterns.items():
            # import 및 self.strategy 호출 등은 제외
            lines = code.split('\n')
            for i, line in enumerate(lines, 1):
                if 'import' in line.lower() or line.strip().startswith('#'):
                    continue
                if 'self.strategy' in line or 'AlphaX7Core' in line:
                    continue
                if re.search(pattern, line, re.IGNORECASE):
                    found.append(f"{name}(L{i})")
        
        if found:
            print(f"  ⚠️ {desc}: 직접계산 {len(found)}개 발견")
            for f in found[:3]: print(f"     - {f}")
            warnings.append(f"{file_path} 직접계산")
        else:
            print(f"  ✅ {desc}: Core 위임됨")
            passes.append(f"{file_path} 위임")

# ============================================================
# [3] 봉마감 로직 검증
# ============================================================
print("\n" + "=" * 70)
print("[3] 봉마감 확정 로직")
print("=" * 70)

print("\n[3-1] 1H 패턴/4H 트렌드: 마지막 봉 제외")
print("-" * 50)
if strategy.exists() or bot.exists():
    s_code = strategy.read_text(encoding='utf-8') if strategy.exists() else ""
    b_code = bot.read_text(encoding='utf-8') if bot.exists() else ""
    combined = s_code + b_code
    
    if '[:-1]' in combined or 'iloc[:-1]' in combined or 'iloc[-2]' in combined:
        passes.append("봉마감 확정 로직")
        print("  ✅ 봉마감 확정 로직(iloc[:-1] 등) 존재")
    else:
        print("  ❌ 봉마감 로직 미확인")
        errors.append("봉마감 미확정")

# ============================================================
# [4] 파라미터 일치 검증
# ============================================================
print("\n" + "=" * 70)
print("[4] 파라미터 일치 검증")
print("=" * 70)

if strategy.exists() and bot.exists():
    s_code = strategy.read_text(encoding='utf-8')
    b_code = bot.read_text(encoding='utf-8')
    
    # ATR mult 검증
    s_atr = re.search(r"'atr_mult':\s*([0-9.]+)", s_code)
    b_atr = re.search(r"DEFAULT_ATR_MULT\s*=\s*([0-9.]+)", b_code)
    
    if s_atr and b_atr:
        if s_atr.group(1) == b_atr.group(1):
            print(f"  ✅ atr_mult: {s_atr.group(1)} (일치)")
            passes.append("atr_mult 일치")
        else:
            print(f"  ❌ atr_mult 불일치: {s_atr.group(1)} vs {b_atr.group(1)}")
            errors.append("atr_mult 불일치")

# ============================================================
# [5] 함수 호출 체인 검증
# ============================================================
print("\n" + "=" * 70)
print("[5] 함수 호출 체인")
print("=" * 70)

print("\n[5-1] unified_bot → strategy_core")
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    if 'self.strategy.manage_position_realtime' in code:
        print("  ✅ manage_position_realtime 호출 확인")
        passes.append("Bot→Core 연결")
    else:
        print("  ❌ manage_position_realtime 호출 없음")
        errors.append("Bot→Core 단절")

print("\n[5-2] multi_sniper → strategy_core")
if sniper.exists():
    code = sniper.read_text(encoding='utf-8')
    if 'manage_position_realtime' in code:
        print("  ✅ manage_position_realtime 호출 확인")
        passes.append("Sniper→Core 연결")
    else:
        print("  ❌ manage_position_realtime 호출 없음")
        errors.append("Sniper→Core 단절")

# ============================================================
# [8] 문법 검사
# ============================================================
print("\n" + "=" * 70)
print("[8] 문법 검사")
print("=" * 70)

import py_compile
syntax_files = ['core/unified_bot.py', 'core/strategy_core.py', 'core/multi_sniper.py']

for f in syntax_files:
    fp = base / f
    if fp.exists():
        try:
            py_compile.compile(str(fp), doraise=True)
            print(f"  ✅ {f}: 정상")
            passes.append(f"{f} 문법")
        except Exception as e:
            print(f"  ❌ {f}: {e}")
            errors.append(f"{f} 문법오류")

# ============================================================
# 최종 결과
# ============================================================
print("\n" + "=" * 70)
print("📊 심층 검증 최종 결과")
print("=" * 70)

print(f"\n✅ 통과: {len(passes)}개")
print(f"⚠️ 경고: {len(warnings)}개")
print(f"❌ 오류: {len(errors)}개")

if errors:
    print("\n🔴 오류 목록:")
    for e in errors: print(f"  - {e}")
else:
    print("\n🎉 모든 핵심 연결고리 검증 통과!")
    print("\n📦 빌드 명령:")
    print("  cd C:\\매매전략")
    print("  pyinstaller staru_clean.spec --noconfirm")

print("\n결과 공유해줘")
