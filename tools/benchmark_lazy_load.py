"""Lazy Load 성능 벤치마크

Phase 1-C: 데이터 연속성 보장 성능 측정

벤치마크 목표:
1. Parquet 읽기 시간 (5-15ms 예상)
2. 병합 처리 시간
3. Parquet 쓰기 시간 (10-20ms 예상)
4. 총 소요 시간 (30-50ms 목표)
5. 파일 크기 (압축률 92% 확인)
"""

import time
import pandas as pd
import tempfile
import shutil
from pathlib import Path
from core.data_manager import BotDataManager


def benchmark_lazy_load():
    """Lazy Load 성능 측정"""
    print("=" * 80)
    print("Lazy Load 아키텍처 성능 벤치마크")
    print("=" * 80)

    # 임시 캐시 디렉토리 생성
    temp_dir = tempfile.mkdtemp()
    print(f"\n임시 캐시 디렉토리: {temp_dir}\n")

    try:
        manager = BotDataManager('bybit', 'BTCUSDT')
        # cache_dir을 임시 디렉토리로 변경
        manager.cache_dir = Path(temp_dir)

        # 1. 초기 데이터 (35,000개 - 1년치)
        print("1. 초기 데이터 생성 중 (35,000개)...")
        initial_start = time.time()

        for i in range(35000):
            manager.append_candle({
                'timestamp': pd.Timestamp('2024-01-01') + pd.Timedelta(minutes=15 * i),
                'open': 100.0,
                'high': 101.0,
                'low': 99.0,
                'close': 100.0,
                'volume': 1000.0
            }, save=(i % 100 == 0))  # 100개마다 저장

            if (i + 1) % 10000 == 0:
                print(f"   - {i + 1:,}개 완료...")

        # 마지막 저장
        manager._save_with_lazy_merge()
        initial_elapsed = time.time() - initial_start
        print(f"   ✅ 완료: {initial_elapsed:.2f}초\n")

        # 2. Lazy Load 성능 측정 (100회)
        print("2. Lazy Load 성능 측정 (100회)...")
        times = []
        for i in range(100):
            start = time.time()
            manager.append_candle({
                'timestamp': pd.Timestamp('2025-01-01') + pd.Timedelta(minutes=15 * i),
                'open': 100.0,
                'high': 101.0,
                'low': 99.0,
                'close': 100.0,
                'volume': 1000.0
            })
            elapsed = time.time() - start
            times.append(elapsed * 1000)  # ms

        # 3. 통계 출력
        print("\n" + "=" * 80)
        print("성능 통계")
        print("=" * 80)
        print(f"평균:   {sum(times) / len(times):.2f}ms")
        print(f"최소:   {min(times):.2f}ms")
        print(f"최대:   {max(times):.2f}ms")
        print(f"중앙값: {sorted(times)[len(times) // 2]:.2f}ms")
        print(f"P95:    {sorted(times)[int(len(times) * 0.95)]:.2f}ms")
        print(f"P99:    {sorted(times)[int(len(times) * 0.99)]:.2f}ms")

        # 4. 파일 크기 확인
        entry_file = manager.get_entry_file_path()
        file_size_kb = entry_file.stat().st_size / 1024
        print("\n" + "=" * 80)
        print("파일 정보")
        print("=" * 80)
        print(f"Parquet 파일 크기: {file_size_kb:.2f}KB")

        # 5. 데이터 개수 확인
        df = pd.read_parquet(entry_file)
        df_entry_len = len(manager.df_entry_full) if manager.df_entry_full is not None else 0
        print(f"저장된 캔들 수:    {len(df):,}개")
        print(f"메모리 캔들 수:    {df_entry_len:,}개")

        # 6. 압축률 계산
        uncompressed_size_kb = len(df) * 8 * 8 / 1024  # 8컬럼 × 8바이트
        compression_ratio = (1 - file_size_kb / uncompressed_size_kb) * 100
        print(f"압축률:           {compression_ratio:.1f}%")

        # 7. 메모리 효율 계산
        memory_size_kb = df_entry_len * 8 * 8 / 1024
        print(f"\n메모리 사용:      {memory_size_kb:.2f}KB (vs {file_size_kb:.2f}KB 파일)")
        print(f"메모리 절약:      {(file_size_kb / memory_size_kb):.1f}배")

        # 8. CPU 부하 계산
        avg_time_ms = sum(times) / len(times)
        interval_ms = 15 * 60 * 1000  # 15분
        cpu_load_pct = (avg_time_ms / interval_ms) * 100
        print(f"\n15분봉 CPU 부하:  {cpu_load_pct:.4f}%")

        # 9. 디스크 수명 추정
        writes_per_day = 96  # 15분봉
        daily_write_mb = (file_size_kb / 1024) * writes_per_day
        yearly_write_gb = daily_write_mb * 365 / 1024
        ssd_lifetime_tbw = 150  # TBW
        estimated_years = (ssd_lifetime_tbw * 1000) / yearly_write_gb
        print(f"\n일일 쓰기량:      {daily_write_mb:.2f}MB")
        print(f"연간 쓰기량:      {yearly_write_gb:.2f}GB")
        print(f"SSD 수명 (150TBW): {estimated_years:,.0f}년")

        # 10. 성공 기준 확인
        print("\n" + "=" * 80)
        print("성공 기준 확인")
        print("=" * 80)
        avg_time = sum(times) / len(times)
        checks = [
            (avg_time < 100, f"평균 I/O 시간 < 100ms: {avg_time:.2f}ms {'✅' if avg_time < 100 else '❌'}"),
            (file_size_kb < 500, f"파일 크기 < 500KB: {file_size_kb:.2f}KB {'✅' if file_size_kb < 500 else '❌'}"),
            (df_entry_len == 1000, f"메모리 1000개 제한: {df_entry_len}개 {'✅' if df_entry_len == 1000 else '❌'}"),
            (len(df) == 35100, f"Parquet 전체 보존: {len(df):,}개 {'✅' if len(df) == 35100 else '❌'}"),
            (compression_ratio > 90, f"압축률 > 90%: {compression_ratio:.1f}% {'✅' if compression_ratio > 90 else '❌'}"),
        ]

        for passed, message in checks:
            print(f"  {message}")

        all_passed = all(c[0] for c in checks)
        print("\n" + "=" * 80)
        if all_passed:
            print("✅ 모든 성공 기준 통과!")
        else:
            print("❌ 일부 기준 미달")
        print("=" * 80)

    finally:
        # 임시 디렉토리 정리
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"\n임시 디렉토리 정리 완료")


def benchmark_read_performance():
    """Parquet 읽기 성능 측정"""
    print("\n" + "=" * 80)
    print("Parquet 읽기 성능 벤치마크")
    print("=" * 80)

    # 임시 캐시 디렉토리 생성
    temp_dir = tempfile.mkdtemp()

    try:
        manager = BotDataManager('bybit', 'BTCUSDT')
        manager.cache_dir = Path(temp_dir)

        # 35,000개 데이터 생성
        print("\n테스트 데이터 생성 중...")
        for i in range(35000):
            manager.append_candle({
                'timestamp': pd.Timestamp('2024-01-01') + pd.Timedelta(minutes=15 * i),
                'open': 100.0,
                'high': 101.0,
                'low': 99.0,
                'close': 100.0,
                'volume': 1000.0
            }, save=(i % 1000 == 0))

        manager._save_with_lazy_merge()

        # 읽기 성능 측정 (100회)
        print("Parquet 읽기 성능 측정 (100회)...")
        entry_file = manager.get_entry_file_path()
        read_times = []

        for _ in range(100):
            start = time.time()
            df = pd.read_parquet(entry_file)
            elapsed = time.time() - start
            read_times.append(elapsed * 1000)  # ms

        print("\n읽기 성능 통계:")
        print(f"  평균:   {sum(read_times) / len(read_times):.2f}ms")
        print(f"  최소:   {min(read_times):.2f}ms")
        print(f"  최대:   {max(read_times):.2f}ms")
        print(f"  중앙값: {sorted(read_times)[len(read_times) // 2]:.2f}ms")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    # 메인 벤치마크
    benchmark_lazy_load()

    # 읽기 성능 벤치마크
    benchmark_read_performance()

    print("\n" + "=" * 80)
    print("벤치마크 완료")
    print("=" * 80)
