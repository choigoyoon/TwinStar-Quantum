
from pathlib import Path
import sys

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent
bot = base / 'core' / 'unified_bot.py'

if not bot.exists():
    print("❌ unified_bot.py not found")
    sys.exit(1)

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

print("=" * 60)
print("unified_bot.py 핵심 로직 검증")
print("=" * 60)

issues = []

# 1. 봉 마감 → 진입 연결
print("\n[1] 봉 마감 → 진입 흐름")
in_candle_close = False
found_process = False
found_execute = False

for i, line in enumerate(lines):
    if 'def _on_candle_close' in line:
        in_candle_close = True
        print(f"  L{i+1}: _on_candle_close 시작")
    
    if in_candle_close:
        if '_process_new_candle' in line:
            found_process = True
            print(f"  L{i+1}: → _process_new_candle 호출 ✅")
        if line.strip().startswith('def ') and '_on_candle_close' not in line:
            break

if not found_process:
    issues.append("_on_candle_close에서 _process_new_candle 미호출")
    print("  ❌ _process_new_candle 호출 없음!")

# 2. _process_new_candle → execute_entry 연결
print("\n[2] _process_new_candle → execute_entry")
in_process = False
found_continue = False
found_live_entry = False

for i, line in enumerate(lines):
    if 'def _process_new_candle' in line:
        in_process = True
        print(f"  L{i+1}: _process_new_candle 시작")
    
    if in_process:
        if '_continue_backtest' in line:
            found_continue = True
            print(f"  L{i+1}: → _continue_backtest 호출 ✅")
        if '_execute_live_entry' in line:
            found_live_entry = True
            print(f"  L{i+1}: → _execute_live_entry 호출 ✅")
        if line.strip().startswith('def ') and '_process_new_candle' not in line:
            break

if not found_continue:
    issues.append("_process_new_candle에서 _continue_backtest 미호출")
if not found_live_entry:
    issues.append("_process_new_candle에서 _execute_live_entry 미호출")

# 3. _execute_live_entry → execute_entry 연결
print("\n[3] _execute_live_entry → execute_entry")
in_live = False
found_exec = False

for i, line in enumerate(lines):
    if 'def _execute_live_entry' in line:
        in_live = True
        print(f"  L{i+1}: _execute_live_entry 시작")
    
    if in_live:
        if 'self.execute_entry' in line:
            found_exec = True
            print(f"  L{i+1}: → execute_entry 호출 ✅")
        if line.strip().startswith('def ') and '_execute_live_entry' not in line:
            break

if not found_exec:
    issues.append("_execute_live_entry에서 execute_entry 미호출")

# 4. run() 루프에서 candle_queue 처리
print("\n[4] run() 루프 내 캔들 처리")
in_run = False
found_queue_get = False
found_process_in_run = False

for i, line in enumerate(lines):
    if 'def run(' in line and 'self' in line:
        in_run = True
        print(f"  L{i+1}: run() 시작")
    
    if in_run:
        if 'candle_queue.get' in line:
            found_queue_get = True
            print(f"  L{i+1}: → candle_queue.get ✅")
        if '_process_new_candle' in line and 'def ' not in line:
            found_process_in_run = True
            print(f"  L{i+1}: → _process_new_candle 호출 ✅")
        if line.strip().startswith('def ') and 'def run(' not in line:
            break

if not found_queue_get:
    issues.append("run()에서 candle_queue.get 없음")
if not found_process_in_run:
    issues.append("run()에서 _process_new_candle 미호출")

# 5. pending_signals 크기 제한
print("\n[5] pending_signals 크기 제한")
if 'deque' in code and 'maxlen' in code and 'pending_signals' in code:
    # maxlen 값 추출
    import re
    match = re.search(r'pending_signals\s*=\s*deque\([^)]*maxlen\s*=\s*(\d+)', code)
    if match:
        maxlen = match.group(1)
        print(f"  ✅ deque(maxlen={maxlen}) 설정됨")
    else:
        print("  ✅ deque + maxlen 있음")
else:
    issues.append("pending_signals에 maxlen 없음")
    print("  ❌ maxlen 없음!")

# 6. 현물 숏 차단
print("\n[6] 현물 숏 차단 (execute_entry 내)")
in_exec = False
found_spot_block = False

for i, line in enumerate(lines):
    if 'def execute_entry' in line:
        in_exec = True
    
    if in_exec:
        if ('upbit' in line.lower() or 'bithumb' in line.lower()) and 'short' in line.lower():
            found_spot_block = True
            print(f"  L{i+1}: 현물 숏 차단 ✅")
            print(f"    {line.strip()[:60]}")
        if line.strip().startswith('def ') and 'execute_entry' not in line:
            break

if not found_spot_block:
    issues.append("execute_entry에 현물 숏 차단 없음")
    print("  ❌ 현물 숏 차단 없음!")

# 결과
print("\n" + "=" * 60)
print("검증 결과")
print("=" * 60)

if issues:
    print(f"❌ 문제: {len(issues)}개")
    for i in issues:
        print(f"  - {i}")
else:
    print("✅ 모든 핵심 로직 정상")
    print("\n진입 흐름:")
    print("  WS 봉마감 → _on_candle_close")
    print("           → _process_new_candle")
    print("           → _continue_backtest")
    print("           → _execute_live_entry")
    print("           → execute_entry (실제 주문)")
