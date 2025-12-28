
from pathlib import Path
import os
import sys

# Ensure proper encoding for printing to console in Windows if needed
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print("=" * 60)
print("1. UPBIT fetchTime 에러 분석")
print("=" * 60)

# 1. upbit 관련 파일 찾기
upbit_files = list(base.rglob('*upbit*.py'))
print(f"\n[1] UPBIT 관련 파일: {len(upbit_files)}개")
for f in upbit_files:
    print(f"  - {f.relative_to(base)}")

# 2. fetchTime 호출 위치 찾기
print(f"\n[2] fetchTime 호출 위치:")
for py in base.rglob('*.py'):
    try:
        code = py.read_text(encoding='utf-8', errors='ignore')
        if 'fetchTime' in code:
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if 'fetchTime' in line:
                    print(f"  {py.relative_to(base)} L{i+1}: {line.strip()[:60]}")
    except:
        pass

# 3. upbit_exchange.py 내용 확인
print(f"\n[3] UPBIT 어댑터 분석:")
for f in upbit_files:
    if 'exchange' in f.name:
        code = f.read_text(encoding='utf-8', errors='ignore')
        
        # fetchTime 메서드 있는지
        has_fetch = 'def fetchTime' in code or 'def fetch_time' in code
        print(f"  {f.name}: fetchTime 메서드: {'있음' if has_fetch else '❌ 없음'}")
        
        # 시간 관련 처리
        if 'time' in code.lower():
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if 'def ' in line and 'time' in line.lower():
                    print(f"    L{i+1}: {line.strip()}")

print("\n" + "=" * 60)
print("2. 현물(SPOT) 숏 거래 버그 분석")
print("=" * 60)

# 1. 백테스트에서 숏 허용 여부 확인
print("\n[1] 백테스트 숏 처리 로직:")
files_to_check = [
    'core/strategy_core.py',
    'core/unified_bot.py',
    'parameter_optimizer.py'
]

for rel in files_to_check:
    fpath = base / rel
    if not fpath.exists():
        continue
    
    code = fpath.read_text(encoding='utf-8', errors='ignore')
    lines = code.split('\n')
    
    print(f"\n📁 {rel}:")
    
    # short 관련 로직
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(k in line_lower for k in ['short', 'direction', 'spot', 'market_type']):
            # Filter for likely relevant lines definitions or conditions
            if 'def ' in line or 'if ' in line or 'todo' in line_lower or 'market_type' in line:
                print(f"  L{i+1}: {line.strip()[:70]}")

# 2. UPBIT 어댑터에서 market_type 확인
print("\n[2] UPBIT market_type 설정:")
for py in base.rglob('*upbit*.py'):
    code = py.read_text(encoding='utf-8', errors='ignore')
    if 'market_type' in code or 'spot' in code.lower():
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if 'market_type' in line or 'spot' in line.lower():
                print(f"  {py.name} L{i+1}: {line.strip()[:60]}")

# 3. 백테스트 방향 필터 확인
print("\n[3] run_backtest 방향 필터:")
strategy = base / 'core' / 'strategy_core.py'
if strategy.exists():
    code = strategy.read_text(encoding='utf-8', errors='ignore')
    
    # run_backtest 함수 내 direction 처리
    in_backtest = False
    for i, line in enumerate(code.split('\n')):
        if 'def run_backtest' in line:
            in_backtest = True
        if in_backtest:
            if 'direction' in line.lower() or 'long' in line.lower() or 'short' in line.lower():
                print(f"  L{i+1}: {line.strip()[:70]}")
            if in_backtest and line.strip().startswith('def ') and 'run_backtest' not in line:
                break
