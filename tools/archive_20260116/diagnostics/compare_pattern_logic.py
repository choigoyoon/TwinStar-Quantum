"""백테스트 vs 실매매 패턴 감지 로직 상세 비교"""
from pathlib import Path

base = Path(r'C:\매매전략')
strategy = base / 'core' / 'strategy_core.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 패턴 감지 로직 비교: strategy_core vs unified_bot")
print("=" * 70)

# 1) strategy_core.py 분석 (백테스트)
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    print("\n[백테스트] strategy_core.py")
    print("-" * 40)
    
    # 패턴 감지 함수
    for i, line in enumerate(lines, 1):
        if 'def ' in line and ('pattern' in line.lower() or 'signal' in line.lower() or 'detect' in line.lower()):
            print(f"  L{i}: {line.strip()}")
    
    # W/M 패턴 조건
    print("\n  W/M 패턴 조건:")
    for i, line in enumerate(lines, 1):
        if ("'W'" in line or "'M'" in line or '"W"' in line or '"M"' in line) and ('pattern' in line.lower() or '==' in line):
            print(f"    L{i}: {line.strip()[:80]}")
    
    # RSI 조건
    print("\n  RSI 조건:")
    for i, line in enumerate(lines, 1):
        if 'rsi' in line.lower() and ('<' in line or '>' in line or '<=' in line or '>=' in line):
            print(f"    L{i}: {line.strip()[:80]}")

# 2) unified_bot.py 분석 (실매매)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    print("\n" + "=" * 70)
    print("[실매매] unified_bot.py")
    print("-" * 40)
    
    # 패턴 감지 함수
    for i, line in enumerate(lines, 1):
        if 'def ' in line and ('pattern' in line.lower() or 'signal' in line.lower() or 'detect' in line.lower()):
            print(f"  L{i}: {line.strip()}")
    
    # W/M 패턴 조건
    print("\n  W/M 패턴 조건:")
    wm_count = 0
    for i, line in enumerate(lines, 1):
        if ("'W'" in line or "'M'" in line or '"W"' in line or '"M"' in line) and ('pattern' in line.lower() or '==' in line):
            if wm_count < 10:
                print(f"    L{i}: {line.strip()[:80]}")
            wm_count += 1
    if wm_count > 10:
        print(f"    ... 외 {wm_count - 10}개")
    
    # RSI 조건
    print("\n  RSI 조건:")
    rsi_count = 0
    for i, line in enumerate(lines, 1):
        if 'rsi' in line.lower() and ('<' in line or '>' in line):
            if rsi_count < 10:
                print(f"    L{i}: {line.strip()[:80]}")
            rsi_count += 1
    if rsi_count > 10:
        print(f"    ... 외 {rsi_count - 10}개")

# 3) 핵심 차이점
print("\n" + "=" * 70)
print("🎯 핵심 비교 포인트")
print("-" * 40)

# strategy_core에서 run_backtest 찾기
if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    if 'run_backtest' in code:
        print("✅ strategy_core: run_backtest() 존재")
        # 진입 조건 추출
        lines = code.split('\n')
        in_backtest = False
        for i, line in enumerate(lines, 1):
            if 'def run_backtest' in line:
                in_backtest = True
            if in_backtest and ('entry' in line.lower() or 'enter' in line.lower() or 'long' in line.lower() or 'short' in line.lower()):
                print(f"    L{i}: {line.strip()[:70]}")
                if i > 100 and 'def ' in lines[i] if i < len(lines) else False:
                    break

print("\n결과 공유해줘 - 패턴 감지 조건이 어디서 다른지 확인하자")
