"""이어가기 로직 전체 추적"""
from pathlib import Path
import json
import os
import sys

base = Path(r'C:\매매전략')
bot = base / 'core' / 'unified_bot.py'

print("=" * 70)
print("🔍 이어가기 로직 추적")
print("=" * 70)

# 1) 진입 시 상태 저장
print("\n[1] 진입 시 save_state 호출")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        if 'execute_entry' in line or 'place_market_order' in line:
            # 주변에 save_state 있는지
            context = lines[max(0,i-5):min(len(lines),i+15)]
            for j, ctx in enumerate(context):
                if 'save_state' in ctx:
                    print(f"  L{i+j-5}: save_state 호출 위치 확인")
                    print(f"       {ctx.strip()[:60]}")

# 2) 저장되는 데이터 구조
print("\n[2] save_state 저장 데이터")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    in_save = False
    for i, line in enumerate(lines, 1):
        if 'def save_state' in line:
            in_save = True
            print(f"  L{i}: {line.strip()}")
            continue
        if in_save:
            if line.strip().startswith('def ') and 'save_state' not in line:
                in_save = False
                break
            if 'position' in line.lower() or 'entry' in line.lower() or 'sl' in line.lower():
                print(f"  L{i}: {line.strip()[:65]}")

# 3) 실제 bot_state 파일 확인
print("\n[3] 실제 bot_state 파일 (최근 캐시 포함)")
print("-" * 50)
# Paths.CACHE가 보통 data/cache 또는 cache이므로 둘 다 확인
cache_dir = base / 'data' / 'cache'
if not cache_dir.exists():
    cache_dir = base / 'cache'

state_files = list(base.glob('bot_state*.json')) + list(cache_dir.glob('bot_state*.json')) if cache_dir.exists() else list(base.glob('bot_state*.json'))
if state_files:
    for sf in state_files[:5]:
        print(f"  📄 {sf.name}")
        try:
            data = json.loads(sf.read_text(encoding='utf-8'))
            if 'position' in data:
                print(f"     position: {data['position']}")
            if 'entry_price' in data or 'entry' in data:
                entry = data.get('entry_price') or data.get('entry')
                sl = data.get('sl_price') or data.get('current_sl')
                print(f"     entry: {entry}, sl: {sl}")
            if 'bt_state' in data:
                bt_pos = data['bt_state'].get('position')
                print(f"     bt_state_pos: {bt_pos}")
        except:
            print("     파싱 실패")
else:
    print("  ❌ bot_state 파일 없음")

# 4) load_state 후 트레일링 연결
print("\n[4] load_state → manage_position 연결")
print("-" * 50)
if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    
    # run() 함수에서 load_state 후 뭘 하는지
    in_run = False
    found_load = False
    for i, line in enumerate(lines, 1):
        if 'def run(' in line:
            in_run = True
        if in_run:
            if line.strip().startswith('def '): # 다른 함수 시작하면 종료
                if 'run(' not in line:
                    in_run = False
                    continue
            
            if 'load_state' in line or '_run_backtest_to_now' in line or 'sync_position' in line:
                print(f"  L{i}: {line.strip()[:65]}")
            if 'manage_position' in line:
                print(f"  L{i}: {line.strip()[:65]}")

# 5) 트레일링 시작 조건
print("\n[5] 트레일링 시작 조건 (Core 로직)")
print("-" * 50)
core_file = base / 'core' / 'strategy_core.py'
if core_file.exists():
    code = core_file.read_text(encoding='utf-8')
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        if '0.8' in line and ('trail' in line.lower() or 'r' in line.lower()):
            print(f"  L{i}: {line.strip()[:70]}")
elif bot.exists(): # 만약 core가 아닌 bot에 있다면
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        if '0.8' in line and ('trail' in line.lower() or 'r' in line.lower()):
            print(f"  L{i}: {line.strip()[:70]}")

print("\n" + "=" * 70)
print("📋 이어가기 체크리스트 (진단 결과)")
print("-" * 50)
