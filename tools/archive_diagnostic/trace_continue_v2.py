"""이어가기 로직 전체 추적 (V2 - Concise)"""
from pathlib import Path
import json
import os

base = Path(__file__).parent
bot = base / 'core' / 'unified_bot.py'
core = base / 'core' / 'strategy_core.py'

print("=" * 70)
print("🔍 이어가기 로직 추적 (Concise)")
print("=" * 70)

def find_lines(file_path, queries, context_range=(5, 10)):
    if not file_path.exists(): return
    code = file_path.read_text(encoding='utf-8')
    lines = code.split('\n')
    results = []
    for i, line in enumerate(lines, 1):
        if any(q in line for q in queries):
            start = max(0, i-context_range[0])
            end = min(len(lines), i+context_range[1])
            results.append((i, lines[start:end]))
    return results

# [1] 진입 시 save_state
print("\n[1] Entry & Save State")
res = find_lines(bot, ['execute_entry', 'place_market_order'], (2, 5))
if res:
    for line_num, context in res:
        for j, ctx in enumerate(context):
            if 'save_state' in ctx:
                print(f"  L{line_num+j-2}: {ctx.strip()}")

# [2] save_state 데이터 구조
print("\n[2] Save State Data Structure")
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    in_func = False
    for i, line in enumerate(lines, 1):
        if 'def save_state' in line: in_func = True
        if in_func:
            if 'state = {' in line or "'position':" in line or "'bt_state':" in line:
                print(f"  L{i}: {line.strip()}")
            if line.strip().startswith('def ') and 'save_state' not in line: in_func = False

# [3] bot_state 파일들
print("\n[3] Actual State Files")
files = list(base.glob('bot_state*.json')) + list((base / 'data/cache').glob('bot_state*.json')) + list((base / 'cache').glob('bot_state*.json'))
for f in files[:5]:
    print(f"  📄 {f.name}")
    try: 
        d = json.loads(f.read_text(encoding='utf-8'))
        print(f"     Pos: {d.get('position')}, BT_Pos: {d.get('bt_state',{}).get('position')}")
    except: print("     Error")

# [4] Run Loop flow
print("\n[4] Run Loop Flow")
res = find_lines(bot, ['def run(', 'load_state(', 'sync_position(', '_run_backtest_to_now('], (0, 30))
if res:
    for line_num, context in res:
        if 'def run(' in context[0]:
            for j, ctx in enumerate(context):
                if any(q in ctx for q in ['load_state', 'sync_position', '_run_backtest_to_now', 'manage_position']):
                    print(f"  L{line_num+j}: {ctx.strip()}")

# [5] 0.8R Trail Condition
print("\n[5] Trail Condition (0.8R)")
res = find_lines(core, ['0.8', 'trail_start'], (1, 1))
if res:
    for line_num, context in res:
        for ctx in context:
            if '0.8' in ctx: print(f"  L{line_num}: {ctx.strip()}")

print("\n" + "=" * 70)
