
from pathlib import Path
import re
import sys

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(__file__).parent

print("=" * 60)
print("API 시간 동기화 + WS + 봉마감 정밀 검증")
print("=" * 60)

issues = []

# ============================================
# 1. API 시간 자동 동기화
# ============================================
print("\n[1] API 시간 자동 동기화")

bot = base / 'core' / 'unified_bot.py'
if not bot.exists():
    print("❌ unified_bot.py not found")
    sys.exit(1)

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

# 시간 오프셋 계산 함수
if 'def get_server_time_offset' in code:
    print("  ✅ get_server_time_offset 함수 존재")
    
    # 어떤 거래소 지원?
    for i, line in enumerate(lines):
        if 'def get_server_time_offset' in line:
            for j in range(i, min(i+30, len(lines))):
                if 'endpoints' in lines[j] and '{' in lines[j]:
                    print(f"  L{j+1}: 거래소별 엔드포인트 정의")
                if "'bybit'" in lines[j] or "'binance'" in lines[j]:
                    print(f"    {lines[j].strip()[:60]}")
            break
else:
    issues.append("get_server_time_offset 없음")

# 시간 오프셋 적용
if 'EXCHANGE_TIME_OFFSET' in code:
    print("  ✅ EXCHANGE_TIME_OFFSET 변수")
    
    # 어디서 적용?
    for i, line in enumerate(lines):
        if 'time.time' in line and 'EXCHANGE_TIME_OFFSET' in line:
            print(f"  L{i+1}: time.time에 오프셋 적용")
            break

# Monkey Patch 확인
if '_hooked_time' in code or 'time.time = ' in code:
    print("  ✅ time.time Monkey Patch 적용")

# 주기적 동기화
if 'start_periodic_sync' in code:
    print("  ✅ 주기적 시간 동기화 함수")
    
    # run()에서 호출하는지
    for i, line in enumerate(lines):
        if 'start_periodic_sync' in line and 'def ' not in line:
            print(f"  L{i+1}: 호출 - {line.strip()[:50]}")

# ============================================
# 2. WS가 API 시간에 연동되는가?
# ============================================
print("\n[2] WS ↔ API 시간 연동")

# WS 연결 시 시간 동기화
ws_files = list(base.rglob('ws_handler.py'))
if ws_files:
    ws_code = ws_files[0].read_text(encoding='utf-8', errors='ignore')
    
    # WS에서 서버 시간 사용?
    if 'time.time' in ws_code:
        print("  ✅ ws_handler: time.time 사용 (Monkey Patch 적용됨)")
    
    # WS 메시지 타임스탬프 처리
    if 'timestamp' in ws_code.lower():
        print("  ✅ ws_handler: timestamp 처리")
        
        # 서버 시간 vs 로컬 시간 비교?
        for i, line in enumerate(ws_code.split('\n')):
            if 'timestamp' in line.lower() and ('server' in line.lower() or 'offset' in line.lower()):
                print(f"    L{i+1}: {line.strip()[:60]}")

# unified_bot에서 WS 시간 처리
print("\n  unified_bot WS 시간 처리:")
for i, line in enumerate(lines):
    if '_on_candle_close' in line and 'def ' in line:
        # 함수 내부에서 시간 처리
        for j in range(i, min(i+50, len(lines))):
            if 'timestamp' in lines[j].lower() and ('ms' in lines[j] or '1000' in lines[j]):
                print(f"    L{j+1}: {lines[j].strip()[:60]}")
        break

# ============================================
# 3. 봉 마감 시간 정확성
# ============================================
print("\n[3] 봉 마감 시간 정확성")

# 봉 마감 감지 로직
if 'candle_queue' in code:
    print("  ✅ candle_queue로 봉 마감 이벤트 수신")

# WS에서 봉 마감 판단 기준
if ws_files:
    ws_code = ws_files[0].read_text(encoding='utf-8', errors='ignore')
    
    # is_closed 또는 confirm 필드 사용?
    if 'is_closed' in ws_code or 'confirm' in ws_code or 'closed' in ws_code.lower():
        print("  ✅ 봉 마감 플래그 체크 (is_closed/confirm)")
    else:
        print("  ⚠️ 봉 마감 플래그 체크 확인 필요")
        
    # 봉 마감 시간 계산
    if 'minute' in ws_code.lower() and ('0' in ws_code or '15' in ws_code or '60' in ws_code):
        print("  ✅ 분 단위 봉 마감 체크")

# ============================================
# 4. 거래소별 WS 시간 처리
# ============================================
print("\n[4] 거래소별 WS 구현")

exchanges_dir = base / 'exchanges'
for ex_file in exchanges_dir.glob('*_exchange.py'):
    ex_code = ex_file.read_text(encoding='utf-8', errors='ignore')
    name = ex_file.stem.replace('_exchange', '')
    
    has_ws = 'start_websocket' in ex_code
    has_time_sync = 'fetchTime' in ex_code or 'time_offset' in ex_code.lower()
    has_candle_cb = 'on_candle' in ex_code.lower() or 'kline' in ex_code.lower()
    
    ws_status = '✅' if has_ws else '❌'
    time_status = '✅' if has_time_sync else '❌'
    cb_status = '✅' if has_candle_cb else '❌'
    
    print(f"  {name}: WS={ws_status} Time={time_status} Candle={cb_status}")

# ============================================
# 5. 시간 동기화 흐름 추적
# ============================================
print("\n[5] 시간 동기화 흐름")

# 봇 시작 시 시간 동기화
flow = []
for i, line in enumerate(lines):
    if 'get_server_time_offset' in line and 'def ' not in line:
        flow.append(f"L{i+1}: get_server_time_offset 호출")
    if 'start_periodic_sync' in line and 'def ' not in line:
        flow.append(f"L{i+1}: start_periodic_sync 시작")
    if '_start_websocket' in line and 'def ' not in line:
        flow.append(f"L{i+1}: WS 시작")

print("  실행 순서:")
for f in flow[:10]:
    print(f"    {f}")

# ============================================
# 6. 봉 마감 → 데이터 저장 → 진입 타이밍
# ============================================
print("\n[6] 봉 마감 → 저장 → 진입 타이밍")

# _on_candle_close 내부 순서
print("  _on_candle_close 내부 흐름:")
in_func = False
for i, line in enumerate(lines):
    if 'def _on_candle_close' in line:
        in_func = True
        print(f"    L{i+1}: 함수 시작")
    if in_func:
        if '_process_new_candle' in line and 'def ' not in line:
            print(f"    L{i+1}: → _process_new_candle")
        if 'candle_queue.put' in line:
            print(f"    L{i+1}: → candle_queue.put")
        if line.strip().startswith('def ') and '_on_candle_close' not in line:
            break

# _process_new_candle 내부 순서
print("\n  _process_new_candle 내부 흐름:")
in_func = False
for i, line in enumerate(lines):
    if 'def _process_new_candle' in line:
        in_func = True
        print(f"    L{i+1}: 함수 시작")
    if in_func:
        if 'pd.to_datetime' in line:
            print(f"    L{i+1}: → timestamp 변환")
        if 'df_entry_full' in line and 'concat' in line:
            print(f"    L{i+1}: → 데이터 병합")
        if '_save' in line.lower() and 'parquet' in line.lower():
            print(f"    L{i+1}: → Parquet 저장")
        if '_continue_backtest' in line:
            print(f"    L{i+1}: → 신호 체크")
        if '_execute_live_entry' in line:
            print(f"    L{i+1}: → 진입 실행")
        if line.strip().startswith('def ') and '_process_new_candle' not in line:
            break

# ============================================
# 7. 시간 관련 잠재적 문제
# ============================================
print("\n" + "=" * 60)
print("잠재적 시간 문제")
print("=" * 60)

print("""
[체크 1] UTC vs 로컬 시간
  - 거래소 API: UTC 사용
  - 로컬 시간: KST (+9시간)
  - 혼용 시 봉 마감 시점 오차 발생

[체크 2] WS 메시지 지연
  - 네트워크 지연: 100ms ~ 1s
  - 봉 마감 후 메시지 도착까지 시간차
  - 이 사이 가격 변동 = 슬리피지

[체크 3] 시간 동기화 주기
  - 30분마다 동기화
  - 그 사이 시간 drift 가능
  - API 호출 시 시간 오차로 401 발생

[체크 4] 국내 거래소 (Upbit/Bithumb)
  - 서버 시간 API 없음
  - 로컬 시간 사용 → PC 시간이 틀리면 문제
""")

# ============================================
# 결과
# ============================================
print("=" * 60)
print("검증 결과")
print("=" * 60)

if issues:
    print(f"❌ 문제: {len(issues)}개")
    for i in issues:
        print(f"  - {i}")
else:
    print("✅ 기본 시간 동기화 로직 존재")
    
print("""
[권장 추가 검증]
1. 봇 실행 후 로그에서 시간 오프셋 확인
   → [TIME] offset=X.XXXs 로그 확인
   
2. WS 봉 마감 시간 vs 실제 시간 비교
   → [WS] Candle closed 로그 시간 확인
   
3. 진입 시점 가격 vs 봉 마감가 비교
   → 슬리피지 수치 확인
""")
