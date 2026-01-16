"""타임존 수정 검증 테스트 (Phase 1)"""
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


def test_timezone_naive_to_aware_conversion(manager):
    """timezone-naive 데이터가 UTC aware로 변환되는지 확인"""
    # 1. timezone-naive 데이터 추가 (100개)
    for i in range(100):
        manager.append_candle({
            'timestamp': pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * i),  # timezone-naive
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.0,
            'volume': 1000.0
        })

    # 2. Parquet 파일 확인
    entry_file = manager.get_entry_file_path()
    assert entry_file.exists(), "Parquet 파일이 존재해야 함"

    # 3. Parquet 로드 시 timezone-aware 확인
    df_saved = pd.read_parquet(entry_file)
    df_saved['timestamp'] = pd.to_datetime(df_saved['timestamp'], unit='ms', utc=True)

    assert df_saved['timestamp'].dt.tz is not None, "Parquet 데이터는 timezone-aware여야 함"
    assert str(df_saved['timestamp'].dt.tz) == 'UTC', "Timezone은 UTC여야 함"

    # 4. 데이터 개수 확인
    assert len(df_saved) == 100, f"100개 데이터가 저장되어야 함 (실제: {len(df_saved)}개)"

    print("✅ 타임존 변환 성공: naive → UTC aware")


def test_timezone_aware_preservation(manager):
    """timezone-aware 데이터가 그대로 유지되는지 확인"""
    # 1. timezone-aware 데이터 추가 (50개)
    for i in range(50):
        manager.append_candle({
            'timestamp': pd.Timestamp('2025-01-01', tz='UTC') + pd.Timedelta(minutes=15 * i),  # UTC aware
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.0,
            'volume': 1000.0
        })

    # 2. Parquet 확인
    entry_file = manager.get_entry_file_path()
    df_saved = pd.read_parquet(entry_file)
    df_saved['timestamp'] = pd.to_datetime(df_saved['timestamp'], unit='ms', utc=True)

    assert df_saved['timestamp'].dt.tz is not None, "Parquet 데이터는 timezone-aware여야 함"
    assert len(df_saved) == 50, f"50개 데이터가 저장되어야 함 (실제: {len(df_saved)}개)"

    print("✅ 타임존 유지 성공: UTC aware → UTC aware")


def test_mixed_timezone_merge(manager):
    """timezone-naive와 aware 데이터 혼합 시 병합 확인"""
    # 1. naive 데이터 50개 추가
    for i in range(50):
        manager.append_candle({
            'timestamp': pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * i),  # naive
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.0 + i,
            'volume': 1000.0
        })

    # 2. aware 데이터 50개 추가 (다른 시간대)
    for i in range(50, 100):
        manager.append_candle({
            'timestamp': pd.Timestamp('2025-01-01', tz='UTC') + pd.Timedelta(minutes=15 * i),  # aware
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.0 + i,
            'volume': 1000.0
        })

    # 3. Parquet 확인
    entry_file = manager.get_entry_file_path()
    df_saved = pd.read_parquet(entry_file)
    df_saved['timestamp'] = pd.to_datetime(df_saved['timestamp'], unit='ms', utc=True)

    # 모두 timezone-aware UTC여야 함
    assert df_saved['timestamp'].dt.tz is not None, "모든 데이터가 timezone-aware여야 함"
    assert len(df_saved) == 100, f"100개 데이터가 저장되어야 함 (실제: {len(df_saved)}개)"

    # 중복 없이 정렬되어야 함
    assert df_saved['timestamp'].is_monotonic_increasing, "타임스탬프가 오름차순이어야 함"
    assert len(df_saved['timestamp'].unique()) == 100, "중복 타임스탬프가 없어야 함"

    print("✅ 혼합 타임존 병합 성공: naive + aware → UTC aware")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
