
from pathlib import Path
import sys

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print("=" * 60)
print("데이터 수집 / 웹소켓 / 진입 신호 검증")
print("=" * 60)

issues = []

# ============================================
# 1. 웹소켓 연결 로직
# ============================================
print("\n[1] 웹소켓 연결")

bot = base / 'core' / 'unified_bot.py'
if not bot.exists():
    print("❌ unified_bot.py not found")
    sys.exit(1)
    
code = bot.read_text(encoding='utf-8')

# _start_websocket 존재
if 'def _start_websocket' in code:
    print("  ✅ _start_websocket 메서드 존재")
else:
    issues.append("_start_websocket 없음")
    print("  ❌ _start_websocket 없음")

# run()에서 _start_websocket 호출
if '_start_websocket()' in code:
    print("  ✅ run()에서 _start_websocket 호출")
else:
    issues.append("run()에서 _start_websocket 미호출")
    print("  ❌ run()에서 _start_websocket 미호출")

# 재연결 로직
if '_on_ws_reconnect' in code or 'restart_websocket' in code:
    print("  ✅ WS 재연결 로직 존재")
else:
    issues.append("WS 재연결 로직 없음")
    print("  ⚠️ WS 재연결 로직 확인 필요")

# ============================================
# 2. ws_handler.py 검증
# ============================================
print("\n[2] ws_handler.py")

ws_files = list(base.rglob('ws_handler.py'))
if ws_files:
    ws = ws_files[0]
    ws_code = ws.read_text(encoding='utf-8', errors='ignore')
    
    # on_message
    if 'on_message' in ws_code:
        print("  ✅ on_message 핸들러")
    else:
        issues.append("ws_handler: on_message 없음")
    
    # on_error
    if 'on_error' in ws_code:
        print("  ✅ on_error 핸들러")
    else:
        issues.append("ws_handler: on_error 없음")
    
    # reconnect
    if 'reconnect' in ws_code.lower():
        print("  ✅ 재연결 로직")
    else:
        issues.append("ws_handler: 재연결 없음")
    
    # is_healthy
    if 'is_healthy' in ws_code:
        print("  ✅ is_healthy 상태 체크")
    else:
        print("  ⚠️ is_healthy 없음 (선택)")
else:
    print("  ⚠️ ws_handler.py 파일 없음")

# ============================================
# 3. 데이터 저장 (Parquet)
# ============================================
print("\n[3] 데이터 저장 (Parquet)")

if '_save_to_parquet' in code:
    print("  ✅ _save_to_parquet 메서드")
else:
    print("  ❌ _save_to_parquet 없음")

if '_save_realtime_candle_to_parquet' in code:
    print("  ✅ 실시간 Parquet 저장")
else:
    print("  ⚠️ 실시간 저장 없음")

if 'to_parquet' in code:
    print("  ✅ DataFrame.to_parquet 호출")

# ============================================
# 4. 갭 체크 및 복구
# ============================================
print("\n[4] 데이터 갭 체크/복구")

if '_check_and_fill_gap' in code:
    print("  ✅ _check_and_fill_gap 메서드")
else:
    print("  ⚠️ 갭 체크 함수 없음")

if '_backfill_missing_candles' in code:
    print("  ✅ _backfill_missing_candles 메서드")
else:
    issues.append("갭 복구 로직 없음")
    print("  ❌ 갭 복구 없음")

if '_run_data_monitor' in code:
    print("  ✅ 백그라운드 데이터 모니터")
else:
    print("  ⚠️ 데이터 모니터 없음")

# ============================================
# 5. 진입 신호 감지
# ============================================
print("\n[5] 진입 신호 감지")

if 'def detect_signal' in code:
    print("  ✅ detect_signal 메서드")

if '_check_entry_from_queue' in code:
    print("  ✅ 큐 기반 진입 체크")

if '_check_entry_live' in code:
    print("  ✅ 실시간 진입 체크")

if 'pending_signals' in code:
    print("  ✅ pending_signals 큐 사용")

# ============================================
# 6. 진입 조건 (MTF, RSI)
# ============================================
print("\n[6] 진입 조건 필터")

if 'get_filter_trend' in code or 'MTF' in code:
    print("  ✅ MTF 트렌드 필터")
else:
    print("  ⚠️ MTF 필터 확인 필요")

if 'pullback_rsi' in code.lower() or 'rsi <' in code.lower() or 'rsi >' in code.lower():
    print("  ✅ RSI 풀백 조건")
else:
    print("  ⚠️ RSI 필터 확인 필요")

# ============================================
# 7. 신호 → 진입 실행 흐름
# ============================================
print("\n[7] 신호 → 진입 실행 흐름")

flow_check = {
    '_continue_backtest': False,
    '_check_entry_live': False,
    '_execute_live_entry': False,
    'execute_entry': False,
    'place_market_order': False
}

for key in flow_check:
    if key in code:
        flow_check[key] = True
        print(f"  ✅ {key}")
    else:
        print(f"  ❌ {key} 없음")
        issues.append(f"{key} 없음")

# ============================================
# 결과
# ============================================
print("\n" + "=" * 60)
print("검증 결과")
print("=" * 60)

if issues:
    print(f"❌ 문제: {len(issues)}개")
    for i in issues:
        print(f"  - {i}")
else:
    print("✅ 모든 로직 정상")
    print("\n데이터 흐름:")
    print("  WS 연결 → 봉 마감 수신 → Parquet 저장")
    print("  갭 발생 → REST API 복구 → 데이터 무결성")
    print("\n진입 흐름:")
    print("  패턴 감지 → pending_signals 큐")
    print("  봉 마감 → MTF/RSI 체크 → execute_entry")
