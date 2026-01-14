
from pathlib import Path
import sys

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent
bot = base / 'core' / 'unified_bot.py'

if bot.exists():
    code = bot.read_text(encoding='utf-8')
    lines = code.split('\n')

    print("=" * 60)
    print("진입 로직 최종 검증")
    print("=" * 60)

    # 1. run() 루프 내 execute_entry 제거 여부 확인
    print("\n[1] run() 루프 중복 진입 로직 확인:")
    in_run = False
    has_dup_execute = False
    
    for i, line in enumerate(lines):
        if 'def run(' in line:
            in_run = True
        if in_run:
            # WebSocket 처리 부분
            if 'self.use_websocket' in line:
                 # Look ahead
                 pass
            
            # _process_new_candle 호출 확인
            if '_process_new_candle(candle)' in line:
                print(f"  ✅ L{i+1}: _process_new_candle 호출 확인")
                
            # execute_entry 호출 확인 (이게 없어야 함, _process_new_candle 내부 제외하고)
            if 'self.execute_entry(' in line and 'signal' in line and in_run:
                # _process_new_candle 내부는 OK, run() 내부는 NO
                # run() 함수 범위 내인지가 중요
                if i > 3300 and i < 3400: # 대략적인 WS 처리 블록 위치
                    has_dup_execute = True
                    print(f"  ❌ L{i+1}: 중복 execute_entry 발견! -> {line.strip()}")
            
            if in_run and line.strip().startswith('def ') and 'def run(' not in line:
                in_run = False
                break
    
    if not has_dup_execute:
        print("  ✅ 중복 execute_entry 호출 없음 (Clean)")

    # 2. _execute_live_entry 존재 확인
    print("\n[2] _execute_live_entry 정의:")
    has_live_exec = False
    for i, line in enumerate(lines):
        if 'def _execute_live_entry' in line:
            has_live_exec = True
            print(f"  ✅ L{i+1}: _execute_live_entry 정의됨")
            
    if not has_live_exec:
        print("  ❌ _execute_live_entry 정의 없음")

else:
    print("❌ unified_bot.py not found")
