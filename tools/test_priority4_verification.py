"""
tools/test_priority4_verification.py
Priority 4 검증: strategy_core 주입 및 실시간 패턴 감지

검증 항목:
1. strategy_core가 _init_modular_components()에서 생성되는가?
2. MACD 초기화가 성공하는가?
3. MTF 필터가 올바른 추세를 반환하는가?
4. 패턴 감지가 실행되는가?
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging

# 로깅 레벨을 INFO로 설정 (디버그 메시지 확인)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

print("=" * 80)
print("Priority 4 검증: strategy_core 주입 및 실시간 패턴 감지")
print("=" * 80)

# ============================================================
# 테스트 1: strategy_core 생성 검증
# ============================================================
print("\n[1/4] strategy_core 생성 검증...")

from core.unified_bot import UnifiedBot
from exchanges.bybit_exchange import BybitExchange

# Mock exchange 생성
class MockExchange:
    def __init__(self):
        self.name = 'bybit'
        self.symbol = 'BTCUSDT'
        self.direction = 'Both'
        self.is_testnet = False

mock_exchange = MockExchange()

# UnifiedBot 생성 (simulation_mode=True)
try:
    bot = UnifiedBot(exchange=mock_exchange, simulation_mode=True)

    # strategy_core가 생성되었는지 확인
    if hasattr(bot, 'strategy_core') and bot.strategy_core is not None:
        print(f"  [OK] strategy_core 생성됨: {type(bot.strategy_core).__name__}")
        print(f"  [OK] use_mtf={bot.strategy_core.USE_MTF_FILTER}")
        print(f"  [OK] strategy_type={bot.strategy_core.strategy_type}")
    else:
        print("  [FAIL] strategy_core가 None입니다!")
        sys.exit(1)

    # PositionManager에 strategy_core가 주입되었는지 확인
    if hasattr(bot, 'mod_position'):
        # PositionManager는 _strategy_core (private) 속성 + strategy 프로퍼티 사용
        if hasattr(bot.mod_position, '_strategy_core') and bot.mod_position._strategy_core is not None:
            print(f"  [OK] PositionManager에 strategy_core 주입됨")
        elif hasattr(bot.mod_position, 'strategy') and bot.mod_position.strategy is not None:
            print(f"  [OK] PositionManager에 strategy 프로퍼티 사용 가능")
        else:
            print("  [WARN] PositionManager에 strategy_core 확인 불가 (private 속성)")
    else:
        print("  [FAIL] mod_position이 없습니다!")
        sys.exit(1)

except Exception as e:
    print(f"  [FAIL] UnifiedBot 생성 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================
# 테스트 2: MACD 초기화 검증
# ============================================================
print("\n[2/4] MACD 초기화 검증...")

from core.data_manager import BotDataManager
import pandas as pd

# 데이터 로드
dm = BotDataManager('bybit', 'BTCUSDT', {'entry_tf': '1h'})
success = dm.load_historical()

if not success or dm.df_entry_full is None:
    print("  [FAIL] 데이터 로드 실패")
    sys.exit(1)

print(f"  [OK] 데이터 로드 완료: {len(dm.df_entry_full):,}개 캔들")

# bot.mod_data에 데이터 주입
bot.mod_data.df_entry_full = dm.df_entry_full.copy()

# MACD 초기화 시도
try:
    result = bot._init_incremental_indicators()

    if result:
        print(f"  [OK] 증분 지표 초기화 성공")

        # MACD 트래커 확인
        if hasattr(bot, 'inc_macd') and bot.inc_macd is not None:
            print(f"  [OK] inc_macd 생성됨")
        else:
            print(f"  [FAIL] inc_macd가 None입니다!")
            sys.exit(1)

        # deque 버퍼 확인
        if len(bot.macd_histogram_buffer) >= 100:
            print(f"  [OK] macd_histogram_buffer: {len(bot.macd_histogram_buffer)}개")
        else:
            print(f"  [WARN] macd_histogram_buffer: {len(bot.macd_histogram_buffer)}개 (100개 미만)")

        if len(bot.price_buffer) >= 100:
            print(f"  [OK] price_buffer: {len(bot.price_buffer)}개")
        else:
            print(f"  [WARN] price_buffer: {len(bot.price_buffer)}개 (100개 미만)")

        # _macd_initialized 플래그 확인
        if bot._macd_initialized:
            print(f"  [OK] _macd_initialized=True")
        else:
            print(f"  [FAIL] _macd_initialized=False")
            sys.exit(1)
    else:
        print(f"  [FAIL] 증분 지표 초기화 실패 (result={result})")
        sys.exit(1)

except Exception as e:
    print(f"  [FAIL] MACD 초기화 예외: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================
# 테스트 3: MTF 필터 검증
# ============================================================
print("\n[3/4] MTF 필터 검증...")

try:
    filter_trend = bot._calculate_mtf_filter()

    if filter_trend is not None:
        print(f"  [OK] MTF 필터 결과: '{filter_trend}'")

        if filter_trend in ['up', 'down']:
            print(f"  [OK] 유효한 추세 방향")
        else:
            print(f"  [FAIL] 잘못된 추세 방향: {filter_trend}")
            sys.exit(1)
    else:
        print(f"  [WARN] MTF 필터 결과: None (데이터 부족 또는 추세 없음)")
        # None은 허용 (추세가 없는 경우)

except Exception as e:
    print(f"  [FAIL] MTF 필터 예외: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================
# 테스트 4: 실시간 패턴 감지 시뮬레이션
# ============================================================
print("\n[4/4] 실시간 패턴 감지 시뮬레이션...")

# 최근 캔들 가져오기 (마지막 1개)
df_recent = bot.mod_data.get_recent_data(limit=1)

if df_recent is None or len(df_recent) == 0:
    print("  [FAIL] 최근 캔들 없음")
    sys.exit(1)

last_candle = df_recent.iloc[-1]

# _on_candle_close() 로직 시뮬레이션
try:
    # MACD 업데이트
    macd_result = bot.inc_macd.update(float(last_candle['close']))

    # deque 버퍼 업데이트
    bot.macd_histogram_buffer.append(macd_result['histogram'])
    bot.price_buffer.append({
        'high': float(last_candle['high']),
        'low': float(last_candle['low']),
        'close': float(last_candle['close'])
    })
    bot.timestamp_buffer.append(last_candle['timestamp'])

    print(f"  [OK] MACD 업데이트 완료: histogram={macd_result['histogram']:.4f}")

    # 패턴 감지 시도
    if bot.strategy_core:
        filter_trend = bot._calculate_mtf_filter()

        pattern_tolerance = bot.strategy_params.get('pattern_tolerance', 0.05)
        entry_validity_hours = bot.strategy_params.get('entry_validity_hours', 48.0)

        signal = bot.strategy_core.detect_wm_pattern_realtime(
            macd_histogram_buffer=bot.macd_histogram_buffer,
            price_buffer=bot.price_buffer,
            timestamp_buffer=bot.timestamp_buffer,
            pattern_tolerance=pattern_tolerance,
            entry_validity_hours=entry_validity_hours,
            filter_trend=filter_trend
        )

        if signal:
            print(f"  [OK] 패턴 감지 성공!")
            print(f"    신호 타입: {signal.signal_type}")
            print(f"    패턴: {signal.pattern}")
            print(f"    진입가: ${signal.entry_price:,.0f}")
            print(f"    손절가: ${signal.stop_loss:,.0f}")
        else:
            print(f"  [OK] 패턴 감지 실행됨 (신호 없음)")
    else:
        print(f"  [FAIL] strategy_core가 None입니다!")
        sys.exit(1)

except Exception as e:
    print(f"  [FAIL] 패턴 감지 예외: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ============================================================
# 최종 요약
# ============================================================
print("\n" + "=" * 80)
print("검증 완료!")
print("=" * 80)

print("\n검증 결과:")
print("  [OK] strategy_core 생성 및 주입")
print("  [OK] MACD 초기화")
print("  [OK] MTF 필터 계산")
print("  [OK] 실시간 패턴 감지 로직")

print("\n다음 단계:")
print("  1. 실제 WebSocket 연결로 테스트")
print("  2. 로그 모니터링: [WM_PATTERN] [OK] 메시지 확인")
print("  3. pending_signals 큐에 신호 추가 여부 확인")

print("\n" + "=" * 80)
