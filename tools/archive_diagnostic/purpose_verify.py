from pathlib import Path
import json

base = Path(r'C:\매매전략')

print('=' * 70)
print('🎯 목적 vs 구현 재검증')
print('=' * 70)

# 1) JSON 설정 구조 확인
print('\n📌 [1] JSON 설정 파일 구조')
json_files = list(base.rglob('*.json'))
count = 0
for f in json_files:
    if '__pycache__' not in str(f) and 'node_modules' not in str(f) and 'venv' not in str(f):
        if count > 15: break # 리스트가 너무 길어지지 않게 제한
        print(f'  {f.relative_to(base)}')
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                print(f'    키: {list(data.keys())[:10]}')
        except Exception:

            pass
        count += 1

# 2) MultiSniper / 멀티 심볼 확인
print('\n📌 [2] 멀티 심볼 매매')
sniper = base / 'core' / 'multi_sniper.py'
if sniper.exists():
    code = sniper.read_text(encoding='utf-8', errors='ignore')
    print(f'  ✅ multi_sniper.py 존재 ({len(code.splitlines())}줄)')
    if 'symbols' in code.lower():
        print('  ✅ 다중 심볼 지원')
else:
    # Try alternate name if common in codebase
    unified = base / 'core' / 'unified_bot.py'
    if unified.exists():
        print('  ℹ️ multi_sniper.py는 없으나 unified_bot.py에서 통합 관리 확인 필요')

# 3) 계산식 동일성 확인
print('\n📌 [3] 슬리피지/수수료 계산 위치')
for fname in ['strategy_core.py', 'unified_bot.py', 'optimizer.py']:
    f = base / 'core' / fname
    if f.exists():
        code = f.read_text(encoding='utf-8', errors='ignore')
        lines = code.splitlines()
        
        print(f'\n  {fname}:')
        match_count = 0
        for i, line in enumerate(lines):
            if 'slippage' in line.lower() and ('*' in line or 'pnl' in line.lower()):
                print(f'    L{i+1}: {line.strip()[:80]}')
                match_count += 1
                if match_count > 10: break

# 4) 결과 vs 거래내역 분리 확인
print('\n📌 [4] 결과 vs 거래내역')
results = base / 'GUI' / 'results_widget.py'
if not results.exists(): results = base / 'GUI' / 'result_widget.py'

history = base / 'GUI' / 'history_widget.py'
if not history.exists(): history = base / 'GUI' / 'trade_history_widget.py'

if results.exists():
    code = results.read_text(encoding='utf-8', errors='ignore')
    print(f'  결과 탭 ({results.name}): {"백테스트" if "backtest" in code.lower() else ""} {"최적화" if "optim" in code.lower() else ""}')

if history.exists():
    code = history.read_text(encoding='utf-8', errors='ignore')
    print(f'  거래내역 ({history.name}): {"실매매" if "trade" in code.lower() else ""} {"storage" if "storage" in code.lower() else ""}')

print('\n' + '=' * 70)
