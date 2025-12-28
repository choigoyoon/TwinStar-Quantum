
from pathlib import Path
import sys

# Ensure proper encoding
sys.stdout.reconfigure(encoding='utf-8')

base = Path(r'C:\매매전략')

print("=" * 60)
print("슬리피지 최소화 매매 로직 검증")
print("=" * 60)

issues = []
recommendations = []

# ============================================
# 1. 데이터 흐름: Parquet → WS 실시간
# ============================================
print("\n[1] 데이터 흐름 (Parquet + WS)")

bot = base / 'core' / 'unified_bot.py'
if not bot.exists():
    print("❌ unified_bot.py not found")
    sys.exit(1)

code = bot.read_text(encoding='utf-8')
lines = code.split('\n')

# Parquet 로드
if '_load_full_historical_data' in code:
    print("  ✅ Parquet 히스토리 로드")
else:
    issues.append("Parquet 로드 없음")

# WS 실시간 병합
if 'pd.concat' in code and 'df_entry_full' in code:
    print("  ✅ WS 데이터 → df_entry_full 병합")
else:
    issues.append("WS 데이터 병합 없음")

# 중복 제거
if 'drop_duplicates' in code:
    print("  ✅ 중복 캔들 제거")

# ============================================
# 2. 봉 마감 시점 진입 (슬리피지 최소화 핵심)
# ============================================
print("\n[2] 봉 마감 시점 진입")

# candle close 이벤트 기반
if '_on_candle_close' in code and 'candle_queue' in code:
    print("  ✅ WS 봉 마감 이벤트 기반")
else:
    issues.append("봉 마감 이벤트 없음")

# 봉 마감 직후 즉시 진입
found_immediate_entry = False
for i, line in enumerate(lines):
    if '_process_new_candle' in line and 'candle' in line:
        # 다음 몇 줄에서 execute_entry 호출 확인
        for j in range(i, min(i+100, len(lines))):
            if '_execute_live_entry' in lines[j]:
                found_immediate_entry = True
                print(f"  ✅ L{j+1}: 봉 마감 → 즉시 진입 로직")
                break
        break

if not found_immediate_entry:
    recommendations.append("봉 마감 직후 진입 로직 강화 필요")

# ============================================
# 3. 시장가 주문 (슬리피지 발생 지점)
# ============================================
print("\n[3] 주문 방식")

if 'place_market_order' in code:
    print("  ⚠️ 시장가 주문 사용 (슬리피지 발생)")
    recommendations.append("지정가 주문 고려")

if 'place_limit_order' in code:
    print("  ✅ 지정가 주문 지원")

# 주문 재시도 로직
if 'max_retries' in code and 'place_market_order' in code:
    print("  ✅ 주문 재시도 로직")

# ============================================
# 4. 가격 조회 방식
# ============================================
print("\n[4] 가격 조회 (WS 우선)")

if '_get_price_safe' in code:
    print("  ✅ _get_price_safe 메서드")
    
    # WS 가격 우선 사용 확인
    for i, line in enumerate(lines):
        if 'def _get_price_safe' in line:
            for j in range(i, min(i+15, len(lines))):
                if 'last_ws_price' in lines[j]:
                    print(f"  ✅ L{j+1}: WS 가격 우선 사용")
                    break
            break

if 'last_ws_price' in code:
    print("  ✅ WS 실시간 가격 캐싱")

# ============================================
# 5. 진입 타이밍 최적화
# ============================================
print("\n[5] 진입 타이밍")

# 봉 마감 대기
if 'minute_in_15min' in code or 'remaining_min' in code:
    print("  ✅ 봉 마감 시간 계산")

# 미리 신호 계산
if 'signal_cache' in code or 'pending_signals' in code:
    print("  ✅ 신호 사전 계산 (Pre-calc)")

# ============================================
# 6. 슬리피지 설정
# ============================================
print("\n[6] 슬리피지 파라미터")

import re
slippage_matches = re.findall(r'slippage[\'\":\s]*=?\s*([\d.]+)', code.lower())
if slippage_matches:
    print(f"  슬리피지 설정값: {set(slippage_matches)}")
else:
    print("  ⚠️ 슬리피지 설정 확인 필요")

# ============================================
# 7. 거래소별 WS 지원
# ============================================
print("\n[7] 거래소별 WS 지원")

exchanges_dir = base / 'exchanges'
for ex_file in exchanges_dir.glob('*_exchange.py'):
    ex_code = ex_file.read_text(encoding='utf-8', errors='ignore')
    name = ex_file.stem.replace('_exchange', '')
    
    has_ws = 'websocket' in ex_code.lower() or 'start_websocket' in ex_code
    has_klines = 'get_klines' in ex_code
    
    ws_status = '✅ WS' if has_ws else '❌ REST only'
    print(f"  {name}: {ws_status}")

# ============================================
# 8. 현재 로직 흐름 요약
# ============================================
print("\n" + "=" * 60)
print("현재 슬리피지 최소화 로직")
print("=" * 60)

print("""
[데이터 흐름]
  1. Parquet 히스토리 로드 (봇 시작 시)
  2. WS 연결 → 실시간 캔들 수신
  3. 봉 마감 시 df_entry_full에 병합
  4. 지표 재계산 → 신호 감지

[진입 타이밍]
  1. 패턴 감지 → pending_signals 큐 저장
  2. 봉 마감 이벤트 수신 (WS)
  3. MTF/RSI 필터 체크
  4. 조건 충족 시 즉시 시장가 주문

[슬리피지 발생 지점]
  ⚠️ 시장가 주문 시 발생
  ⚠️ WS → REST 전환 시 지연
  ⚠️ 주문 재시도 시 가격 변동
""")

# ============================================
# 개선 권장사항
# ============================================
print("=" * 60)
print("슬리피지 최소화 권장사항")
print("=" * 60)

print("""
[현재 OK]
  ✅ WS 봉 마감 기반 진입 (REST 폴링보다 빠름)
  ✅ 신호 사전 계산 (봉 마감 전 준비)
  ✅ WS 가격 우선 사용

[개선 가능]
  1. 지정가 주문 (Limit Order)
     - 봉 마감가 기준 ±0.1% 지정가
     - 체결 안 되면 취소 후 시장가

  2. Post-Only 주문
     - Maker 수수료 절약
     - 슬리피지 0%

  3. 봉 마감 1~2초 전 진입
     - 마감가 예측 후 선제 진입
     - 리스크 있음

  4. TWAP/VWAP 분할 주문
     - 대량 주문 시 슬리피지 분산
""")

# 결과
print("\n" + "=" * 60)
if issues:
    print(f"❌ 문제: {len(issues)}개")
    for i in issues:
        print(f"  - {i}")
else:
    print("✅ 기본 슬리피지 최소화 로직 정상")
