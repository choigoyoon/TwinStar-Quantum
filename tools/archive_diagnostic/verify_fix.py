import os
import sys
from pathlib import Path
import py_compile

base = Path(__file__).parent

def run_verify():
    print('=== 수정 사항 검증 ===')

    # 1) 수수료 스케일 확인
    print('\n[1] 수수료 스케일 (strategy_core.py):')
    core = base / 'core' / 'strategy_core.py'
    if core.exists():
        code = core.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        for i, line in enumerate(lines):
            # Checking for the fix pnl - (slippage * 200)
            if 'pnl' in line and ( 'slippage * 200' in line):
                print(f'  L{i+1}: {line.strip()[:100]}')

    # 2) 단리/복리 표시 확인
    print('\n[2] 단리/복리 필드 (backtest_widget.py):')
    bt = base / 'GUI' / 'backtest_widget.py'
    if bt.exists():
        code = bt.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if 'simple_return' in line.lower() or 'compound_return' in line.lower():
                if '_stat_' in line or 'result_stats' in line or 'r.get' in line:
                    print(f'  L{i+1}: {line.strip()[:100]}')

    # 3) 방향 필터 확인
    print('\n[3] 방향 필터 (backtest_widget.py):')
    if bt.exists():
        code = bt.read_text(encoding='utf-8', errors='ignore')
        lines = code.split('\n')
        for i, line in enumerate(lines):
            if 'direction' in line.lower() and ('combo' in line.lower() or 'Both' in line or 'Long' in line):
                if 'self.' in line or 'worker' in line or 'addItems' in line:
                    print(f'  L{i+1}: {line.strip()[:100]}')

    # 4) 문법 검증
    print('\n[4] 문법 검증:')
    for f in [core, bt]:
        if f.exists():
            try:
                py_compile.compile(str(f), doraise=True)
                print(f'  ✅ {f.name}')
            except py_compile.PyCompileError as e:
                print(f'  ❌ {f.name}: {e}')

    print('\n=== 완료 ===')

if __name__ == "__main__":
    run_verify()
