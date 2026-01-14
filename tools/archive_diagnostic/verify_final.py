"""v1.5.2 로직 통합 최종 검증"""
from pathlib import Path
import re

base = Path(__file__).parent
strategy = base / 'core' / 'strategy_core.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔬 v1.5.2 로직 통합 최종 검증")
print("=" * 70)

errors = []
passes = []

# 1) unified_bot 중복 계산 제거 확인
print("\n[1] unified_bot 중복 계산 제거 확인")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    duplicates = []
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        if 'ta.rsi(' in lower or 'talib.rsi(' in lower:
            if 'import' not in lower:
                duplicates.append(f"  L{i}: RSI - {line.strip()[:50]}")
        if 'ta.atr(' in lower or 'talib.atr(' in lower:
            if 'import' not in lower:
                duplicates.append(f"  L{i}: ATR - {line.strip()[:50]}")
    
    if duplicates:
        print(f"  ⚠️ 중복 {len(duplicates)}개:")
        for d in duplicates[:5]:
            print(d)
        errors.append(f"중복 계산 {len(duplicates)}개")
    else:
        print("  ✅ 중복 계산 없음")
        passes.append("중복 제거 ✅")

# 2) strategy_core 핵심 메서드 존재
print("\n[2] strategy_core 핵심 메서드")
print("-" * 50)
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    
    methods = {
        'manage_position_realtime': 'Trailing Stop',
        'get_mtf_trend': '4H 트렌드',
        '_extract_all_signals': '패턴 추출',
        'detect_signal': '시그널 감지',
    }
    
    for m, desc in methods.items():
        if f'def {m}' in code:
            print(f"  ✅ {m}")
            passes.append(f"{desc} ✅")
        else:
            print(f"  ❌ {m} 없음")
            errors.append(f"{desc} 없음")

# 3) 봉마감 데이터만 사용
print("\n[3] 봉마감 확정 데이터 사용")
print("-" * 50)
if strategy.exists() or bot.exists():
    s_code = strategy.read_text(encoding='utf-8') if strategy.exists() else ""
    b_code = bot.read_text(encoding='utf-8') if bot.exists() else ""
    combined = s_code + b_code
    
    if '[:-1]' in combined or 'iloc[:-1]' in combined or '.iloc[-2]' in combined:
        print("  ✅ 마지막 봉 제외 로직 존재")
        passes.append("봉마감 확정 ✅")
    else:
        print("  ❌ 봉마감 로직 미확인")
        errors.append("봉마감 로직 없음")

# 4) unified_bot → strategy_core 호출
print("\n[4] unified_bot → AlphaX7Core 연결")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    
    connections = []
    keywords = ['self.strategy', 'self.core', 'AlphaX7', 'strategy_core']
    for i, line in enumerate(code.split('\n'), 1):
        for kw in keywords:
            if kw in line and 'import' not in line.lower():
                connections.append(f"  L{i}: {line.strip()[:60]}")
                break
    
    if connections:
        print(f"  ✅ Core 연결 {len(connections)}개:")
        for c in connections[:5]:
            print(c)
        passes.append("Core 연결 ✅")
    else:
        print("  ❌ Core 연결 없음")
        errors.append("Core 연결 없음")

# 5) 파라미터 동기화
print("\n[5] 핵심 파라미터 일치")
print("-" * 50)
if strategy.exists() and bot.exists():
    s_code = strategy.read_text(encoding='utf-8')
    b_code = bot.read_text(encoding='utf-8')
    
    # ATR mult 더 구체적인 패턴으로 추출
    s_atr_match = re.search(r"'atr_mult':\s*([0-9.]+)", s_code)
    b_atr_match = re.search(r"DEFAULT_ATR_MULT\s*=\s*([0-9.]+)", b_code)
    
    if s_atr_match and b_atr_match:
        s_val = s_atr_match.group(1)
        b_val = b_atr_match.group(1)
        if s_val == b_val:
            print(f"  ✅ ATR mult: {s_val}")
            passes.append("ATR mult 일치 ✅")
        else:
            print(f"  ⚠️ ATR mult: Core={s_val} vs Bot={b_val}")
            errors.append("ATR mult 불일치")
    else:
        print("  ⚠️ ATR mult 확인 불가")

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
    print("\n수정 후 재검증 필요")
else:
    print("\n🎉 모든 검증 통과!")
    print("\n빌드 진행:")
    print("  cd C:\\매매전략")
    print("  pyinstaller staru_clean.spec --noconfirm")

print("\n결과 공유해줘")
