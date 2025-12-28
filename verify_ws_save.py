
import os

path = r"C:\매매전략\core\unified_bot.py"
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

print("=== WS 캔들 저장 로직 확인 ===\n")

# 1. 캔들 저장 로직
candle_save = "to_parquet" in content or "save_candle" in content
print(f"{'✅' if candle_save else '❌'} 1. 캔들 저장 함수 (to_parquet/save_candle)")

# 2. 봉 마감 감지
candle_close = "candle_close" in content.lower() or "is_closed" in content or "confirm" in content
print(f"{'✅' if candle_close else '❌'} 2. 봉 마감 감지 (confirm/closed)")

# 3. WS 데이터 → DataFrame 추가
ws_append = "append" in content and ("candle" in content.lower() or "kline" in content.lower())
print(f"{'✅' if ws_append else '❌'} 3. WS 캔들 DataFrame 추가")

# ws_handler.py 확인
ws_path = r"C:\매매전략\exchanges\ws_handler.py"
if not os.path.exists(ws_path):
     ws_path = r"C:\매매전략\core\ws_handler.py"

try:
    with open(ws_path, 'r', encoding='utf-8') as f:
        ws = f.read()

    print("\n=== ws_handler.py ===")
    print(f"{'✅' if 'confirm' in ws or 'closed' in ws.lower() else '❌'} 봉 마감 플래그 확인")
    print(f"{'✅' if 'callback' in ws or 'on_candle' in ws else '❌'} 캔들 콜백 함수")
except Exception as e:
    print(f"❌ ws_handler.py 파일 없음: {e}")
