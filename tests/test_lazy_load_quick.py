"""Lazy Load 빠른 검증 테스트 (Phase 1)"""
import pytest
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from core.data_manager import BotDataManager


@pytest.fixture
def temp_cache_dir():
    """임시 캐시 디렉토리 생성"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def manager(temp_cache_dir, monkeypatch):
    """테스트용 BotDataManager 생성"""
    manager = BotDataManager('bybit', 'BTCUSDT')
    monkeypatch.setattr(manager, 'cache_dir', temp_cache_dir)
    return manager


def test_lazy_load_small_dataset(manager):
    """Lazy Load 방식 소규모 데이터 테스트 (500개)"""
    # 1. 500개 캔들 추가
    for i in range(500):
        manager.append_candle({
            'timestamp': pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * i),
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.0,
            'volume': 1000.0
        })

    # 2. 메모리 확인 (500개 < 1000개이므로 모두 유지)
    assert manager.df_entry_full is not None
    assert len(manager.df_entry_full) == 500

    # 3. Parquet 확인 (500개 전체 보존)
    entry_file = manager.get_entry_file_path()
    assert entry_file.exists()

    df_saved = pd.read_parquet(entry_file)
    assert len(df_saved) == 500

    # 4. 타임존 확인
    df_saved['timestamp'] = pd.to_datetime(df_saved['timestamp'], unit='ms', utc=True)
    assert df_saved['timestamp'].dt.tz is not None, "Parquet 데이터는 timezone-aware여야 함"

    print(f"✅ Lazy Load 작동 확인 (500개 데이터)")


def test_lazy_load_memory_limit(manager):
    """메모리 제한 테스트 (1500개 → 1000개)"""
    # 1. 1500개 캔들 추가
    for i in range(1500):
        manager.append_candle({
            'timestamp': pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * i),
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.0 + i,
            'volume': 1000.0
        })

    # 2. 메모리는 1000개로 제한
    assert len(manager.df_entry_full) == 1000, f"메모리는 1000개로 제한되어야 함 (실제: {len(manager.df_entry_full)})"

    # 3. Parquet은 1500개 전체 보존
    entry_file = manager.get_entry_file_path()
    df_saved = pd.read_parquet(entry_file)
    assert len(df_saved) == 1500, f"Parquet은 전체 히스토리를 보존해야 함 (실제: {len(df_saved)}개)"

    # 4. 메모리는 최근 1000개만 유지 (1500개 중 마지막 1000개)
    first_close = manager.df_entry_full['close'].iloc[0]
    last_close = manager.df_entry_full['close'].iloc[-1]
    assert last_close == 1499.0, f"마지막 값은 1499여야 함 (실제: {last_close})"
    assert first_close >= 500.0, f"첫 값은 500 이상이어야 함 (실제: {first_close})"

    # 5. Parquet은 전체 유지
    df_saved['timestamp'] = pd.to_datetime(df_saved['timestamp'], unit='ms', utc=True)
    df_saved = df_saved.sort_values('timestamp').reset_index(drop=True)
    assert df_saved['close'].iloc[0] == 0.0, "Parquet은 처음부터 (index 0~1499)"
    assert df_saved['close'].iloc[-1] == 1499.0

    print("✅ 메모리 제한 작동: 1500개 → 메모리 1000개, Parquet 1500개")


def test_lazy_load_no_data_loss_small(manager):
    """데이터 손실 없음 검증 (200개)"""
    # 1. 데이터 추가
    timestamps = []
    for i in range(200):
        ts = pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * i)
        timestamps.append(ts)
        manager.append_candle({
            'timestamp': ts,
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.0 + i,
            'volume': 1000.0
        })

    # 2. 모든 타임스탬프 보존 확인
    df_saved = pd.read_parquet(manager.get_entry_file_path())
    df_saved['timestamp'] = pd.to_datetime(df_saved['timestamp'], unit='ms', utc=True)

    saved_timestamps = set(df_saved['timestamp'])
    # timezone-naive → UTC aware로 변환
    expected_timestamps = set(pd.to_datetime(timestamps).tz_localize('UTC'))

    missing = expected_timestamps - saved_timestamps
    assert len(missing) == 0, f"누락된 타임스탬프 {len(missing)}개"

    print("✅ 데이터 손실 없음: 200개 모두 보존")


def test_lazy_load_duplicate_handling(manager):
    """중복 타임스탬프 처리 (마지막 값 유지)"""
    # 1. 동일 타임스탬프에 다른 값 3회 추가
    ts = pd.Timestamp('2025-01-01')
    manager.append_candle({'timestamp': ts, 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'volume': 1000})
    manager.append_candle({'timestamp': ts, 'open': 100, 'high': 101, 'low': 99, 'close': 200, 'volume': 1000})
    manager.append_candle({'timestamp': ts, 'open': 100, 'high': 101, 'low': 99, 'close': 300, 'volume': 1000})

    # 2. 마지막 값만 유지
    df_saved = pd.read_parquet(manager.get_entry_file_path())
    assert len(df_saved) == 1, "중복 제거되어 1개만 남아야 함"

    df_saved['timestamp'] = pd.to_datetime(df_saved['timestamp'], unit='ms', utc=True)
    assert df_saved['close'].iloc[0] == 300, "마지막 값(300)이 유지되어야 함"

    print("✅ 중복 처리: 마지막 값 유지")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
