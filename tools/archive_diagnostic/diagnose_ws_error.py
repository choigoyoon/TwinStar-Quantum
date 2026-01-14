from pathlib import Path
import re

base = Path(__file__).parent

# 1. ws_handler.py 메서드 확인
ws = base / 'exchanges/ws_handler.py'
try:
    code = ws.read_text(encoding='utf-8', errors='ignore')
    print("ws_handler.py 메서드 목록:")
    print("=" * 40)
    methods = re.findall(r'def (\w+)\(self', code)
    for m in methods:
        print(f"  - {m}")
except Exception as e:
    print(f"ws_handler.py 읽기 실패: {e}")

# 2. bybit_exchange.py에서 호출하는 메서드
bybit = base / 'exchanges/bybit_exchange.py'
try:
    code2 = bybit.read_text(encoding='utf-8', errors='ignore')
    print("\nbybit_exchange.py에서 호출:")
    print("=" * 40)
    if 'run_sync' in code2:
        idx = code2.find('run_sync')
        print(f"  run_sync 호출 발견 (위치: {idx})")
        # context showing
        start = max(0, idx - 50)
        end = min(len(code2), idx + 50)
        print(f"  >> {code2[start:end]}")
    else:
        print("  run_sync 없음")
except Exception as e:
    print(f"bybit_exchange.py 읽기 실패: {e}")

# 3. 대안 메서드 확인
print("\n대안 메서드 확인:")
for alt in ['start', 'run', 'connect', 'run_forever']:
    if f'def {alt}(' in code:
        print(f"  ✅ {alt} 메서드 존재")
