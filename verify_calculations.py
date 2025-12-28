# verify_calculations.py - 코드 실행 순서 + 계산식 분석
import os
import re

base_path = r'C:\매매전략'

print("=" * 60)
print("코드 실행 순서 + 계산식 분석")
print("=" * 60)

# 파일 로드
bot_path = os.path.join(base_path, 'core/unified_bot.py')
strategy_path = os.path.join(base_path, 'core/strategy_core.py')

with open(bot_path, 'r', encoding='utf-8') as f:
    bot_content = f.read()
    bot_lines = bot_content.split('\n')

with open(strategy_path, 'r', encoding='utf-8') as f:
    strategy_content = f.read()

# [1] 파라미터 로드
print("\n[1] 파라미터 로드")
for i, line in enumerate(bot_lines):
    if 'ATR_MULT' in line and '=' in line and 'params' in line:
        print(f"  L{i+1}: {line.strip()[:60]}")
    if 'TRAIL_START' in line and '=' in line and 'params' in line:
        print(f"  L{i+1}: {line.strip()[:60]}")

# [2] ATR 계산
print("\n[2] ATR 계산식")
atr_idx = strategy_content.find('def calculate_atr')
if atr_idx != -1:
    atr_end = strategy_content.find('\n    def ', atr_idx + 10)
    atr_code = strategy_content[atr_idx:atr_end if atr_end != -1 else atr_idx+300]
    lines = atr_code.split('\n')[:10]
    for line in lines:
        print(f"  {line[:60]}")

# [3] SL 계산
print("\n[3] SL 계산 (ATR 기반)")
for i, line in enumerate(bot_lines):
    if ('stop_loss' in line.lower() or 'sl' in line.lower()) and 'atr' in line.lower():
        if '=' in line and ('-' in line or '+' in line or '*' in line):
            print(f"  L{i+1}: {line.strip()[:65]}")

# [4] 트레일링 SL
print("\n[4] 트레일링 SL 계산")
for i, line in enumerate(bot_lines):
    if 'trail' in line.lower() and 'extreme' in line.lower():
        print(f"  L{i+1}: {line.strip()[:65]}")
    if 'new_sl' in line.lower() and '=' in line:
        print(f"  L{i+1}: {line.strip()[:65]}")

# [5] PnL 계산
print("\n[5] PnL 계산")
for i, line in enumerate(bot_lines):
    if 'pnl' in line.lower() and ('/' in line or '%' in line):
        if 'entry' in line.lower() or 'exit' in line.lower() or 'price' in line.lower():
            print(f"  L{i+1}: {line.strip()[:65]}")

# [6] 주문 크기
print("\n[6] 주문 크기 계산")
for i, line in enumerate(bot_lines):
    if 'qty' in line.lower() or 'size' in line.lower() or 'amount' in line.lower():
        if '=' in line and ('/' in line or '*' in line):
            if 'capital' in line.lower() or 'balance' in line.lower() or 'risk' in line.lower():
                print(f"  L{i+1}: {line.strip()[:65]}")

# [7] 신호 감지
print("\n[7] 신호 감지 함수")
if 'def detect_signal' in strategy_content:
    print("  OK detect_signal() 존재")
if 'entry_validity' in strategy_content:
    print("  OK entry_validity_hours 사용")
if 'filter_trend' in strategy_content.lower():
    print("  OK 트렌드 필터 사용")

# [8] 실행 순서 요약
print("\n" + "=" * 60)
print("[실행 순서 요약]")
print("=" * 60)
print("""
1. Parquet 로드 -> df_entry_full, df_pattern_full
2. 지표 계산 -> RSI, ATR, EMA, MACD
3. 웹소켓 시작 -> 15분봉 수신
4. 캔들 마감 -> _on_candle_close()
5. 신호 감지 -> detect_signal()
   - 패턴 감지 (W/M)
   - 트렌드 필터 (filter_tf)
   - 유효시간 체크 (entry_validity_hours)
6. 진입 -> execute_entry()
   - ATR 계산
   - SL = price - ATR * atr_mult
   - qty = capital * risk / price
   - place_market_order()
7. 포지션 관리 -> _manage_position_live()
   - 트레일링 SL
   - new_sl = extreme - risk * trail_dist_r
8. 청산 -> _execute_live_close()
   - PnL = (exit - entry) / entry * 100
   - 거래 기록 저장
""")

print("=" * 60)
print("분석 완료")
print("=" * 60)
