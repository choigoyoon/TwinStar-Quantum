"""Strategy Logic Consolidation 검증"""
from pathlib import Path
import pandas as pd
import numpy as np

base = Path(r'C:\매매전략')
strategy = base / 'core' / 'strategy_core.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔬 Single Source of Truth 검증")
print("=" * 70)

issues = []
passes = []

# 1) unified_bot에서 직접 계산하는 중복 로직 찾기
print("\n[1] unified_bot 중복 계산 체크 (제거 대상)")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    duplicates = []
    for i, line in enumerate(lines, 1):
        lower = line.lower()
        # 직접 RSI/ATR 계산
        if 'ta.rsi' in lower or 'talib.rsi' in lower:
            duplicates.append(f"  L{i}: RSI 직접계산 - {line.strip()[:50]}")
        # 직접 ATR 계산 패턴 (unified_bot.py 특유의 numpy 활용 패턴 등)
        if 'np.maximum(highs - lows' in lower or 'np.abs(highs - closes' in lower:
             duplicates.append(f"  L{i}: ATR 직접계산 - {line.strip()[:50]}")
        # 직접 EMA 계산
        if '.ewm(' in lower and 'self.strategy' not in line:
            duplicates.append(f"  L{i}: EMA 직접계산 - {line.strip()[:50]}")
    
    if duplicates:
        print("  ⚠️ 중복 계산 발견:")
        for d in duplicates[:10]:
            print(d)
        issues.append(f"중복 계산 {len(duplicates)}개")
    else:
        print("  ✅ 직접 계산 없음 - Core에 위임됨")
        passes.append("중복 계산 제거 ✅")

# 2) AlphaX7Core 메서드 호출 확인
print("\n[2] AlphaX7Core 메서드 호출 확인")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    
    core_methods = [
        'manage_position_realtime',
        'get_mtf_trend', 
        '_extract_all_signals',
        'detect_signal',
        'calculate_atr',
        'calculate_rsi'
    ]
    
    found_calls = []
    for method in core_methods:
        if method in code:
            found_calls.append(method)
            print(f"  ✅ {method} 호출됨")
        else:
            print(f"  ❓ {method} 호출 없음")
    
    if len(found_calls) >= 3:
        passes.append("Core 메서드 호출 ✅")
    else:
        issues.append("Core 메서드 호출 부족")

# 3) strategy_core에 통합된 메서드 확인
print("\n[3] strategy_core 통합 메서드 확인")
print("-" * 50)
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    
    required = [
        ('manage_position_realtime', 'Trailing Stop 관리'),
        ('get_mtf_trend', '4H 트렌드 필터'),
        ('_extract_all_signals', '패턴 추출'),
    ]
    
    for method, desc in required:
        if f'def {method}' in code:
            print(f"  ✅ {method}: {desc}")
            passes.append(f"{method} ✅")
        else:
            print(f"  ❌ {method}: {desc} 없음")
            issues.append(f"{method} 없음")

# 4) 상태 관리 단순화 확인
print("\n[4] 상태 관리 (Core 출력 사용)")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    
    # Core에서 반환받아 사용하는 패턴
    patterns = ['result =', 'signal =', 'action =', 'decision =']
    core_returns = []
    for i, line in enumerate(code.split('\n'), 1):
        for p in patterns:
            if p in line and 'self.strategy' in line:
                core_returns.append(f"  L{i}: {line.strip()[:60]}")
    
    if core_returns:
        print("  ✅ Core 반환값 사용:")
        for cr in core_returns[:5]:
            print(cr)
        passes.append("상태 관리 단순화 ✅")
    else:
        print("  ⚠️ Core 반환값 사용 패턴 미확인")

# 최종 결과
print("\n" + "=" * 70)
print("📊 Single Source of Truth 검증 결과")
print("=" * 70)

print(f"\n✅ 통과: {len(passes)}개")
for p in passes:
    print(f"  - {p}")

if issues:
    print(f"\n⚠️ 확인 필요: {len(issues)}개")
    for i in issues:
        print(f"  - {i}")

if not issues:
    print("\n🎉 로직 통합 완료!")
    print("\n다음 단계:")
    print("  1. py C:\\매매전략\\verify_calc_sync.py")
    print("  2. pyinstaller staru_clean.spec --noconfirm")

print("\n결과 공유해줘")
