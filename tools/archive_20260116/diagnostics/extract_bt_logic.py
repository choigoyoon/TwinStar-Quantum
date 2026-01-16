"""백테스트 로직 추출 → 실매매 동기화 포인트 찾기"""
from pathlib import Path

base = Path(r'C:\매매전략')
strategy = base / 'core' / 'strategy_core.py'
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🎯 백테스트 로직 추출 (실매매 동기화 기준)")
print("=" * 70)

if strategy.exists():
    code = strategy.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    # run_backtest 함수 전체 추출
    print("\n[1] run_backtest() 핵심 로직")
    print("-" * 50)
    
    in_func = False
    func_lines = []
    indent_level = 0
    
    for i, line in enumerate(lines, 1):
        if 'def run_backtest' in line or 'def _run_backtest' in line:
            in_func = True
            indent_level = len(line) - len(line.lstrip())
        
        if in_func:
            # 진입/청산 관련 라인만
            lower = line.lower()
            if any(kw in lower for kw in ['entry', 'enter', 'long', 'short', 'signal', 'pattern', 'rsi', 'atr', 'sl', 'tp', 'close', 'exit']):
                func_lines.append(f"L{i}: {line.rstrip()[:90]}")
            
            # 다음 함수 시작하면 종료
            if i > 10 and line.strip().startswith('def ') and 'backtest' not in line.lower():
                if len(line) - len(line.lstrip()) <= indent_level:
                    break
    
    for fl in func_lines[:30]:
        print(f"  {fl}")
    if len(func_lines) > 30:
        print(f"  ... 외 {len(func_lines) - 30}개")

    # 시그널 생성 함수
    print("\n[2] 시그널 생성 함수")
    print("-" * 50)
    for i, line in enumerate(lines, 1):
        if 'def ' in line and ('signal' in line.lower() or 'extract' in line.lower()):
            print(f"  L{i}: {line.strip()}")

print("\n" + "=" * 70)
print("🔧 실매매(unified_bot) 동기화 필요 포인트")
print("=" * 70)

if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    # 실매매 진입 함수
    print("\n[3] 실매매 진입 함수 위치")
    for i, line in enumerate(lines, 1):
        if 'def ' in line and ('entry' in line.lower() or 'detect' in line.lower() or 'check' in line.lower()):
            print(f"  L{i}: {line.strip()}")
    
    # 실매매 RSI 조건
    print("\n[4] 실매매 RSI 필터 (수정 대상)")
    rsi_lines = []
    for i, line in enumerate(lines, 1):
        if 'rsi' in line.lower() and ('filter' in line.lower() or '<' in line or '>' in line):
            rsi_lines.append(f"  L{i}: {line.strip()[:80]}")
    for rl in rsi_lines[:10]:
        print(rl)

print("\n" + "=" * 70)
print("📋 동기화 체크리스트")
print("-" * 50)
print("□ 패턴 감지 조건 동일한가?")
print("□ RSI 필터 조건 동일한가?")
print("□ ATR SL 계산 동일한가?")
print("□ 진입 타이밍(캔들 확정) 동일한가?")
print("□ Trailing Stop 로직 동일한가?")
print("\n결과 공유해줘")
