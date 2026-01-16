"""Lazy Load 디버깅 테스트"""
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from core.data_manager import BotDataManager


def test_debug_lazy_load():
    """Lazy Load 동작 디버깅"""
    # 임시 디렉토리
    temp_dir = Path(tempfile.mkdtemp())

    try:
        manager = BotDataManager('bybit', 'BTCUSDT')
        manager.cache_dir = temp_dir

        # 10개씩 3번 추가 (총 30개)
        for batch in range(3):
            print(f"\n=== Batch {batch + 1} ===")
            for i in range(10):
                idx = batch * 10 + i
                manager.append_candle({
                    'timestamp': pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * idx),
                    'open': 100.0,
                    'high': 101.0,
                    'low': 99.0,
                    'close': 100.0 + idx,
                    'volume': 1000.0
                })

            # 배치 후 상태 확인
            print(f"메모리 개수: {len(manager.df_entry_full)}")
            print(f"메모리 close 범위: {manager.df_entry_full['close'].min()} ~ {manager.df_entry_full['close'].max()}")

            # Parquet 확인
            entry_file = manager.get_entry_file_path()
            if entry_file.exists():
                df_saved = pd.read_parquet(entry_file)
                print(f"Parquet 개수: {len(df_saved)}")

                # timestamp를 datetime으로 변환 후 확인
                df_saved['timestamp'] = pd.to_datetime(df_saved['timestamp'], unit='ms', utc=True)
                df_saved = df_saved.sort_values('timestamp').reset_index(drop=True)
                print(f"Parquet close 범위: {df_saved['close'].min()} ~ {df_saved['close'].max()}")
                print(f"Parquet close 값들: {df_saved['close'].tolist()}")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    test_debug_lazy_load()
