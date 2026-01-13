
import os

path = r"C:\매매전략\core\unified_bot.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("=== v1.2.3 패치 적용 확인 ===\n")

# 1. 신호 동기화
sync_check = "[SYNC]" in content or "Synchronized" in content
print(f"{'✅' if sync_check else '❌'} 1. 신호 동기화 ([SYNC] 로그)")

# 2. RSI 풀백 체크
rsi_check = ("< 40" in content or "> 60" in content) and "rsi" in content.lower()
print(f"{'✅' if rsi_check else '❌'} 2. RSI 풀백 조건 (Long<40, Short>60)")

# 3. DataFrame 안전 처리  
df_safe = ".get('type', " in content or ".get('direction', " in content
print(f"{'✅' if df_safe else '❌'} 3. DataFrame 안전 처리")

# 4. 진입 실행 로직
entry_check = "execute_entry" in content
print(f"{'✅' if entry_check else '❌'} 4. execute_entry 함수 존재")

# 5. pending_signals 클리어
clear_check = "pending_signals.clear()" in content or "pending_signals = []" in content
print(f"{'✅' if clear_check else '❌'} 5. pending_signals 클리어")

# 6. 12시간 필터
filter_check = "timedelta(hours=12)" in content or "hours=12" in content
print(f"{'✅' if filter_check else '❌'} 6. 12시간 신호 필터")

# WS traceback
print("\n=== ws_handler.py ===")
ws_path = r"C:\매매전략\exchanges\ws_handler.py"
try:
    with open(ws_path, 'r', encoding='utf-8') as f:
        ws = f.read()
    ws_trace = "traceback" in ws and "format_exc" in ws
    print(f"{'✅' if ws_trace else '❌'} WS 에러 traceback")
except Exception:
    print("❌ ws_handler.py 파일 없음")
