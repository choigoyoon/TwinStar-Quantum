
from pathlib import Path
import sys
import re

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print("=" * 60)
print("데이터 수집 문제 정밀 분석")
print("=" * 60)

issues = []

# ============================================
# 1. 초기 데이터 로드
# ============================================
print("\n[1] 초기 데이터 로드")

bot = base / 'core' / 'unified_bot.py'
if not bot.exists():
    print("❌ unified_bot.py not found")
    sys.exit(1)
    
code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

# Parquet 로드 순서
if '_load_full_historical_data' in code:
    print("  ✅ Parquet 로드 함수 존재")
    
    # 어디서 호출?
    for i, line in enumerate(lines):
        if '_load_full_historical_data()' in line and 'def ' not in line:
            print(f"  L{i+1}: 호출 위치 - {line.strip()[:50]}")
else:
    issues.append("Parquet 로드 없음")

# Parquet 없을 때 REST fallback
if '_fetch_historical_from_rest' in code:
    print("  ✅ REST fallback 존재")
else:
    issues.append("Parquet 없을 때 REST fallback 없음")

# ============================================
# 2. WS 연결 및 데이터 수신
# ============================================
print("\n[2] WS 연결")

# WS 시작 시점
for i, line in enumerate(lines):
    if '_start_websocket()' in line and 'def ' not in line:
        print(f"  L{i+1}: WS 시작 - {line.strip()[:50]}")

# WS 콜백
if '_on_candle_close' in code:
    print("  ✅ 봉 마감 콜백")
    
if '_on_price_update' in code:
    print("  ✅ 가격 업데이트 콜백")

# WS 상태 체크
if '_check_ws_health' in code:
    print("  ✅ WS 상태 체크 함수")
    
    # is_healthy 호출 확인
    if 'is_healthy' in code:
        print("  ✅ is_healthy 호출")
else:
    issues.append("WS 상태 체크 없음")

# ============================================
# 3. 갭 발생 시 복구
# ============================================
print("\n[3] 갭 복구 로직")

if '_backfill_missing_candles' in code:
    print("  ✅ 갭 복구 함수 존재")
    
    # 어디서 호출?
    count = 0
    for i, line in enumerate(lines):
        if '_backfill_missing_candles()' in line and 'def ' not in line:
            count += 1
            print(f"  L{i+1}: 호출 - {line.strip()[:50]}")
    
    if count == 0:
        issues.append("_backfill_missing_candles 호출 없음")
else:
    issues.append("갭 복구 함수 없음")

# 갭 체크 로직
if '_check_and_fill_gap' in code:
    print("  ✅ 갭 체크 함수 존재")

# 백그라운드 모니터
if '_run_data_monitor' in code:
    print("  ✅ 백그라운드 데이터 모니터")
    
    # 주기 확인
    interval = re.search(r'_data_monitor_interval\s*=\s*(\d+)', code)
    if interval:
        print(f"  갭 체크 주기: {interval.group(1)}초")

# ============================================
# 4. WS 끊김 시 처리
# ============================================
print("\n[4] WS 끊김 처리")

if '_on_ws_reconnect' in code:
    print("  ✅ WS 재연결 콜백")
    
    # 재연결 시 갭 복구하는지
    for i, line in enumerate(lines):
        if 'def _on_ws_reconnect' in line:
            for j in range(i, min(i+10, len(lines))):
                if 'backfill' in lines[j].lower():
                    print(f"  L{j+1}: 재연결 시 갭 복구 ✅")
                    break
            break

if 'restart_websocket' in code:
    print("  ✅ WS 재시작 함수")

# ============================================
# 5. 거래소별 API 시간 동기화 (401 원인)
# ============================================
print("\n[5] API 시간 동기화 (401 에러 방지)")

if 'get_server_time_offset' in code:
    print("  ✅ 서버 시간 오프셋 계산")

if 'EXCHANGE_TIME_OFFSET' in code:
    print("  ✅ 시간 오프셋 변수")

if 'start_periodic_sync' in code:
    print("  ✅ 주기적 시간 동기화")
    
    # 주기 확인
    sync_interval = re.search(r'interval_minutes\s*[:=]\s*(\d+)', code)
    if sync_interval:
        print(f"  동기화 주기: {sync_interval.group(1)}분")
    else:
        print("  동기화 주기 확인 불가")
else:
    print("  ⚠️ 주기적 동기화 없음")

# 거래소별 fetchTime
print("\n  거래소별 시간 동기화:")
exchanges = ['bybit', 'binance', 'upbit', 'bithumb', 'bingx', 'okx']
for ex in exchanges:
    found = False
    for f in base.rglob(f'*{ex}*.py'):
        if 'exchange' in f.name.lower():
            try:
                ex_code = f.read_text(encoding='utf-8', errors='ignore')
                has_time = 'fetchTime' in ex_code or 'fetch_time' in ex_code or 'sync_time' in ex_code
                status = '✅' if has_time else '❌'
                print(f"    {ex}: {status}")
                if not has_time:
                    issues.append(f"{ex} 시간 동기화 없음")
                found = True
                break
            except Exception as e:
                pass
    if not found:
        print(f"    {ex}: 파일 없음")

# ============================================
# 6. 데이터 저장
# ============================================
print("\n[6] 실시간 데이터 저장")

if '_save_realtime_candle_to_parquet' in code:
    print("  ✅ 실시간 Parquet 저장")

if 'to_parquet' in code:
    print("  ✅ DataFrame.to_parquet 호출")

# ============================================
# 7. 문제 시나리오 분석
# ============================================
print("\n" + "=" * 60)
print("문제 시나리오")
print("=" * 60)

print("""
[시나리오 1] WS 끊김
  현재: _check_ws_health → restart_websocket → _on_ws_reconnect → backfill
  문제: 재연결 실패 시? REST 폴링으로 전환?

[시나리오 2] API 401 에러
  현재: 시간 오프셋 계산 + 주기적 동기화
  문제: Upbit/Bithumb는 fetchTime 없음 → 로컬 시간 사용

[시나리오 3] Parquet 없음 (첫 실행)
  현재: _fetch_historical_from_rest fallback
  문제: 1000개만 가져옴 → 장기 패턴 감지 불가

[시나리오 4] 장시간 갭 (봇 재시작)
  현재: _run_data_monitor (5분마다 체크)
  문제: 봇 시작 시 갭 체크 하는지?
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
    print("✅ 데이터 수집 로직 정상")
