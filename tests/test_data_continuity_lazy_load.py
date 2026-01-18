"""Lazy Load 아키텍처 검증 테스트

Phase 1-C: 데이터 연속성 보장 (Lazy Load 방식)

테스트 목표:
1. 전체 히스토리 보존 (메모리 1000개 제한에도 불구하고)
2. 데이터 손실 없음 (타임스탬프 보존)
3. 성능 (100ms 이하)
4. 중복 처리 (마지막 값 유지)
"""

import pytest
import pandas as pd
import time
import tempfile
import shutil
from pathlib import Path
from core.data_manager import BotDataManager


@pytest.fixture
def temp_cache_dir():
    """임시 캐시 디렉토리 생성"""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    # 테스트 후 정리
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def manager(temp_cache_dir, monkeypatch):
    """테스트용 BotDataManager 생성"""
    # cache_dir을 임시 디렉토리로 변경
    manager = BotDataManager('bybit', 'BTCUSDT')
    monkeypatch.setattr(manager, 'cache_dir', temp_cache_dir)
    return manager


class TestLazyLoadArchitecture:
    """Lazy Load 아키텍처 테스트"""

    def test_lazy_load_preserves_full_history(self, manager):
        """Lazy Load 방식 전체 히스토리 보존 테스트"""
        # 1. 10,000개 캔들 추가
        for i in range(10000):
            manager.append_candle({
                'timestamp': pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * i),
                'open': 100.0,
                'high': 101.0,
                'low': 99.0,
                'close': 100.0,
                'volume': 1000.0
            })

        # 2. 메모리는 1000개만 유지
        assert manager.df_entry_full is not None, "df_entry_full이 None이면 안 됨"
        assert len(manager.df_entry_full) == 1000, f"메모리는 1000개로 제한되어야 함 (실제: {len(manager.df_entry_full)})"

        # 3. Parquet은 10,000개 전체 보존
        entry_file = manager.get_entry_file_path()
        assert entry_file.exists(), "Parquet 파일이 존재해야 함"

        df_saved = pd.read_parquet(entry_file)
        assert len(df_saved) == 10000, f"Parquet은 전체 히스토리를 보존해야 함 (실제: {len(df_saved)}개)"

    def test_lazy_load_no_data_loss(self, manager):
        """데이터 손실 없음 검증"""
        # 1. 초기 데이터 (5000개)
        timestamps = []
        for i in range(5000):
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

        # 2. 추가 데이터 (5000개)
        for i in range(5000, 10000):
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

        # 3. 모든 타임스탬프 보존 확인
        df_saved = pd.read_parquet(manager.get_entry_file_path())
        df_saved['timestamp'] = pd.to_datetime(df_saved['timestamp'], unit='ms')

        saved_timestamps = set(df_saved['timestamp'])
        expected_timestamps = set(timestamps)

        assert saved_timestamps == expected_timestamps, \
            f"모든 타임스탬프가 보존되어야 함 (누락: {len(expected_timestamps - saved_timestamps)}개)"

    def test_lazy_load_performance(self, manager):
        """Lazy Load 성능 테스트 (100ms 목표)"""
        # 1. 초기 데이터 (1000개)
        for i in range(1000):
            manager.append_candle({
                'timestamp': pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * i),
                'open': 100.0,
                'high': 101.0,
                'low': 99.0,
                'close': 100.0,
                'volume': 1000.0
            })

        # 2. 추가 저장 시간 측정 (Lazy Load 발동)
        start = time.time()
        manager.append_candle({
            'timestamp': pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * 1000),
            'open': 100.0,
            'high': 101.0,
            'low': 99.0,
            'close': 100.0,
            'volume': 1000.0
        })
        elapsed = time.time() - start

        # 3. 100ms 이하 확인 (여유 있게, 목표 30ms)
        assert elapsed < 0.1, f"Lazy Load는 100ms 이하여야 함 (실제: {elapsed * 1000:.2f}ms)"

    def test_lazy_load_duplicate_handling(self, manager):
        """중복 타임스탬프 처리 테스트"""
        # 1. 같은 타임스탬프 여러 번 추가
        ts = pd.Timestamp('2025-01-01 00:00:00')
        for i in range(10):
            manager.append_candle({
                'timestamp': ts,
                'open': 100.0,
                'high': 101.0,
                'low': 99.0,
                'close': 100.0 + i,  # 값은 다름
                'volume': 1000.0
            })

        # 2. 1개만 저장되어야 함 (마지막 값)
        df_saved = pd.read_parquet(manager.get_entry_file_path())
        assert len(df_saved) == 1, f"중복 타임스탬프는 1개만 보존 (실제: {len(df_saved)}개)"

        df_saved['timestamp'] = pd.to_datetime(df_saved['timestamp'], unit='ms')
        assert df_saved.iloc[0]['close'] == 109.0, \
            f"마지막 값이 보존되어야 함 (실제: {df_saved.iloc[0]['close']})"

    def test_websocket_scenario(self, manager):
        """실제 WebSocket 시나리오 테스트"""
        # 1. 초기 히스토리 로드 시뮬레이션 (1000개)
        for i in range(1000):
            manager.append_candle({
                'timestamp': pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * i),
                'open': 100.0,
                'high': 101.0,
                'low': 99.0,
                'close': 100.0,
                'volume': 1000.0
            })

        initial_count = len(pd.read_parquet(manager.get_entry_file_path()))

        # 2. WebSocket으로 100개 추가 수신
        for i in range(100):
            manager.append_candle({
                'timestamp': pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * (1000 + i)),
                'open': 100.0,
                'high': 101.0,
                'low': 99.0,
                'close': 100.0,
                'volume': 1000.0
            })

        # 3. Parquet에 전체 보존 확인
        final_count = len(pd.read_parquet(manager.get_entry_file_path()))
        assert final_count == initial_count + 100, \
            f"WebSocket 데이터가 누적되어야 함 (초기: {initial_count}, 최종: {final_count})"

    def test_lazy_load_large_dataset(self, manager):
        """대용량 데이터셋 테스트 (35,000개 - 1년치)"""
        # 1. 35,000개 캔들 추가 (시간 소요)
        print("\n35,000개 캔들 추가 중...")
        start = time.time()

        for i in range(35000):
            manager.append_candle({
                'timestamp': pd.Timestamp('2024-01-01') + pd.Timedelta(minutes=15 * i),
                'open': 100.0,
                'high': 101.0,
                'low': 99.0,
                'close': 100.0,
                'volume': 1000.0
            }, save=(i % 100 == 0))  # 100개마다 저장 (성능 최적화)

        # 마지막 저장
        manager._save_with_lazy_merge()
        elapsed = time.time() - start

        print(f"총 소요 시간: {elapsed:.2f}초")

        # 2. 메모리는 1000개만
        assert len(manager.df_entry_full) <= 1000, "메모리는 1000개 이하여야 함"

        # 3. Parquet은 35,000개 전체
        df_saved = pd.read_parquet(manager.get_entry_file_path())
        assert len(df_saved) == 35000, f"Parquet은 35,000개 보존해야 함 (실제: {len(df_saved)}개)"

        # 4. 파일 크기 확인 (압축률 확인)
        entry_file = manager.get_entry_file_path()
        file_size_kb = entry_file.stat().st_size / 1024
        print(f"Parquet 파일 크기: {file_size_kb:.2f}KB")

        # 5. 예상 크기 확인 (약 280KB, 여유 있게 500KB 이하)
        assert file_size_kb < 500, f"Parquet 파일이 너무 큼 (실제: {file_size_kb:.2f}KB)"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
