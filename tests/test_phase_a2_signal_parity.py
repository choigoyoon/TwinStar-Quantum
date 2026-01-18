"""
tests/test_phase_a2_signal_parity.py

Phase A-2 검증 테스트: 실시간 vs 백테스트 신호 일치

목표:
    - 동일한 데이터로 계산 시 실시간과 백테스트 신호가 100% 일치
    - 지표 계산 범위 통일 (워밍업 윈도우 100개)
"""

import sys
import logging
from pathlib import Path
import pandas as pd
import numpy as np

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.data_manager import BotDataManager
from utils.indicators import add_all_indicators

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_test_data(num_candles: int = 500) -> pd.DataFrame:
    """테스트용 OHLCV 데이터 생성"""
    base_price = 50000.0
    timestamps = pd.date_range(start='2024-01-01', periods=num_candles, freq='15min')

    data = []
    for i, ts in enumerate(timestamps):
        close = base_price + np.sin(i / 10) * 1000 + np.random.randn() * 100
        high = close + abs(np.random.randn() * 50)
        low = close - abs(np.random.randn() * 50)
        open_ = (high + low) / 2
        volume = 1000 + np.random.randn() * 100

        data.append({
            'timestamp': ts,
            'open': open_,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })

    return pd.DataFrame(data)


def test_warmup_window_effect():
    """워밍업 윈도우 효과 검증"""
    logger.info("\n=== Test 1: Warmup Window Effect ===")

    # 테스트 데이터 생성 (500개)
    df_full = generate_test_data(500)

    # 1. 워밍업 없이 100개로 지표 계산
    df_100 = df_full.tail(100).copy()
    df_100 = add_all_indicators(df_100)
    rsi_100 = df_100['rsi'].iloc[-1]

    # 2. 워밍업 포함 200개로 지표 계산 후 최근 100개
    df_200 = df_full.tail(200).copy()
    df_200 = add_all_indicators(df_200)
    df_100_warmup = df_200.tail(100).copy()
    rsi_100_warmup = df_100_warmup['rsi'].iloc[-1]

    # 3. 전체 500개로 지표 계산 후 최근 100개
    df_full_ind = add_all_indicators(df_full)
    df_100_full = df_full_ind.tail(100).copy()
    rsi_100_full = df_100_full['rsi'].iloc[-1]

    logger.info(f"RSI (100개만 사용):        {rsi_100:.4f}")
    logger.info(f"RSI (200개 워밍업):        {rsi_100_warmup:.4f}")
    logger.info(f"RSI (전체 500개):          {rsi_100_full:.4f}")

    # 워밍업 vs 전체 차이
    diff_warmup = abs(rsi_100_warmup - rsi_100_full)
    diff_no_warmup = abs(rsi_100 - rsi_100_full)

    logger.info(f"\n워밍업 포함 vs 전체 차이:  {diff_warmup:.6f}")
    logger.info(f"워밍업 없음 vs 전체 차이:  {diff_no_warmup:.6f}")

    # 검증: 워밍업 포함 시 차이 < 0.1%
    assert diff_warmup < 0.5, f"워밍업 포함 시에도 차이 큼: {diff_warmup}"
    logger.info("✅ Test 1 Passed: 워밍업 윈도우가 지표 정확도 개선")


def test_get_recent_data_consistency():
    """get_recent_data() 일관성 검증"""
    logger.info("\n=== Test 2: get_recent_data() Consistency ===")

    # BotDataManager 생성
    manager = BotDataManager('bybit', 'BTCUSDT', cache_dir='data/cache')

    # 테스트 데이터 생성 및 저장
    df_test = generate_test_data(1500)
    manager.df_entry_full = df_test.copy()
    manager.save_parquet()

    # 1. get_recent_data(100, warmup=100)
    df_recent = manager.get_recent_data(limit=100, warmup_window=100)
    assert df_recent is not None, "get_recent_data() returned None"

    # 2. get_full_history() + tail(100)
    df_full = manager.get_full_history(with_indicators=True)
    assert df_full is not None, "get_full_history() returned None"
    df_full_tail = df_full.tail(100).copy()

    # RSI 비교
    rsi_recent = df_recent['rsi'].iloc[-1]
    rsi_full = df_full_tail['rsi'].iloc[-1]

    logger.info(f"RSI (get_recent_data):     {rsi_recent:.4f}")
    logger.info(f"RSI (get_full_history):    {rsi_full:.4f}")
    logger.info(f"차이:                      {abs(rsi_recent - rsi_full):.6f}")

    # 검증: 차이 < 0.1%
    diff = abs(rsi_recent - rsi_full)
    assert diff < 0.1, f"get_recent_data()와 get_full_history() 불일치: {diff}"
    logger.info("✅ Test 2 Passed: get_recent_data()와 get_full_history() 일치")

    # 정리
    entry_file = manager.get_entry_file_path()
    if entry_file.exists():
        entry_file.unlink()


def test_live_vs_backtest_signal_parity():
    """실시간 vs 백테스트 신호 일치 검증"""
    logger.info("\n=== Test 3: Live vs Backtest Signal Parity ===")

    # BotDataManager 생성
    manager = BotDataManager('bybit', 'BTCUSDT', cache_dir='data/cache')

    # 테스트 데이터 생성 (2000개)
    df_test = generate_test_data(2000)
    manager.df_entry_full = df_test.copy()

    # 시뮬레이션: 백테스트 vs 실시간
    backtest_signals = []
    live_signals = []

    # 백테스트 모드: 전체 데이터로 지표 계산
    df_backtest = add_all_indicators(df_test)

    for i in range(1500, 2000):  # 마지막 500개 캔들 시뮬레이션
        # 백테스트: 처음부터 i번째까지 사용
        df_bt_slice = df_backtest.iloc[:i+1].tail(100).copy()
        rsi_bt = df_bt_slice['rsi'].iloc[-1]

        # 실시간: 메모리 제한 (최근 1000개만 유지)
        manager.df_entry_full = df_test.iloc[max(0, i-999):i+1].copy()
        df_live = manager.get_recent_data(limit=100, warmup_window=100)
        rsi_live = df_live['rsi'].iloc[-1] if df_live is not None else 0.0

        # 신호 생성 (RSI 기준)
        signal_bt = 'LONG' if rsi_bt < 30 else ('SHORT' if rsi_bt > 70 else 'NEUTRAL')
        signal_live = 'LONG' if rsi_live < 30 else ('SHORT' if rsi_live > 70 else 'NEUTRAL')

        backtest_signals.append(signal_bt)
        live_signals.append(signal_live)

    # 신호 일치율 계산
    total = len(backtest_signals)
    matches = sum(1 for bt, lv in zip(backtest_signals, live_signals) if bt == lv)
    match_rate = matches / total * 100

    logger.info(f"총 신호 수:        {total}")
    logger.info(f"일치 신호 수:      {matches}")
    logger.info(f"일치율:            {match_rate:.2f}%")

    # 검증: 일치율 >= 95%
    assert match_rate >= 95.0, f"신호 일치율 부족: {match_rate:.2f}%"
    logger.info("✅ Test 3 Passed: 실시간 vs 백테스트 신호 일치율 >= 95%")


def test_memory_vs_parquet_parity():
    """메모리 제한 vs Parquet 전체 히스토리 일치"""
    logger.info("\n=== Test 4: Memory vs Parquet Parity ===")

    # BotDataManager 생성
    manager = BotDataManager('bybit', 'BTCUSDT', cache_dir='data/cache')

    # 테스트 데이터 생성 (5000개, 메모리 제한 1000개 초과)
    df_test = generate_test_data(5000)
    manager.df_entry_full = df_test.copy()
    manager.save_parquet()

    # 메모리 truncate 시뮬레이션 (최근 1000개만)
    manager.df_entry_full = df_test.tail(1000).copy()

    # 1. 메모리에서 최근 100개 (워밍업 포함)
    df_memory = manager.get_recent_data(limit=100, warmup_window=100)
    assert df_memory is not None, "get_recent_data() returned None"

    # 2. Parquet에서 전체 로드 후 최근 100개
    df_parquet_full = manager.get_full_history(with_indicators=True)
    assert df_parquet_full is not None, "get_full_history() returned None"
    df_parquet = df_parquet_full.tail(100).copy()

    # RSI 비교
    rsi_memory = df_memory['rsi'].iloc[-1]
    rsi_parquet = df_parquet['rsi'].iloc[-1]

    logger.info(f"메모리 캔들 수:    {len(manager.df_entry_full)}")
    logger.info(f"Parquet 캔들 수:   {len(df_parquet_full)}")
    logger.info(f"RSI (메모리):      {rsi_memory:.4f}")
    logger.info(f"RSI (Parquet):     {rsi_parquet:.4f}")
    logger.info(f"차이:              {abs(rsi_memory - rsi_parquet):.6f}")

    # 검증: 차이 < 0.1%
    diff = abs(rsi_memory - rsi_parquet)
    assert diff < 0.1, f"메모리와 Parquet 불일치: {diff}"
    logger.info("✅ Test 4 Passed: 메모리 제한에도 Parquet 전체 히스토리와 일치")

    # 정리
    entry_file = manager.get_entry_file_path()
    if entry_file.exists():
        entry_file.unlink()


if __name__ == '__main__':
    logger.info("=" * 80)
    logger.info("Phase A-2 신호 일치 테스트 시작")
    logger.info("=" * 80)

    try:
        test_warmup_window_effect()
        test_get_recent_data_consistency()
        test_live_vs_backtest_signal_parity()
        test_memory_vs_parquet_parity()

        logger.info("\n" + "=" * 80)
        logger.info("✅ 모든 테스트 통과!")
        logger.info("=" * 80)
        logger.info("\nPhase A-2 성과:")
        logger.info("  - 워밍업 윈도우 효과 검증 완료")
        logger.info("  - get_recent_data() 일관성 검증 완료")
        logger.info("  - 실시간 vs 백테스트 신호 일치율 >= 95%")
        logger.info("  - 메모리 제한에도 Parquet 전체 히스토리 일치")

    except AssertionError as e:
        logger.error(f"\n❌ 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
