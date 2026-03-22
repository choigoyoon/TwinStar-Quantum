"""
API Timezone 수정 검증 스크립트

timezone_helper.py 유틸리티가 정상 동작하는지 테스트

사용법:
    python tools/test_timezone_fix.py

Author: Claude Opus 4.5
Date: 2026-01-15
"""

import sys
import os
from pathlib import Path

# UTF-8 인코딩 강제
if os.name == 'nt':  # Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 프로젝트 루트 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
from datetime import datetime

from utils.timezone_helper import (
    to_utc_datetime,
    get_current_utc,
    format_timestamp_local,
    normalize_dataframe_timestamps,
    compare_timestamps,
    get_time_difference_seconds
)


def test_1_timestamp_conversion():
    """테스트 1: 타임스탬프 → UTC 변환"""
    print("\n[테스트 1] 타임스탬프 → UTC 변환")
    print("-" * 60)

    timestamp_ms = 1705334400000  # 2024-01-15 12:00:00 UTC
    utc_time = to_utc_datetime(timestamp_ms, unit='ms')

    print(f"입력: {timestamp_ms} ms")
    print(f"UTC:  {utc_time}")
    print(f"Timezone: {utc_time.tz}")

    assert utc_time.tz is not None, "❌ Timezone 없음!"
    assert str(utc_time.tz) == 'UTC', f"❌ Timezone이 UTC가 아님: {utc_time.tz}"

    print("✅ 통과")


def test_2_local_time_conversion():
    """테스트 2: UTC → 로컬 시간 변환"""
    print("\n[테스트 2] UTC → 로컬 시간 변환")
    print("-" * 60)

    timestamp_ms = 1705334400000  # UTC 타임스탬프
    utc_time = to_utc_datetime(timestamp_ms, unit='ms')
    local_str = format_timestamp_local(utc_time, local_tz='Asia/Seoul')

    print(f"UTC: {utc_time}")
    print(f"KST: {local_str}")

    # 시간 차이가 9시간인지 확인 (UTC → KST는 +9시간)
    utc_hour = utc_time.hour
    local_hour = int(local_str.split()[1].split(':')[0])

    # 날짜 경계를 고려한 시간 차이 계산
    hour_diff = (local_hour - utc_hour) % 24

    print(f"시간 차이: {hour_diff}시간 (예상: 9시간)")
    assert hour_diff == 9, f"❌ 로컬 시간 변환 오류: UTC {utc_hour}시 → KST {local_hour}시 (차이 {hour_diff}시간)"

    print("✅ 통과")


def test_3_current_time():
    """테스트 3: 현재 시간"""
    print("\n[테스트 3] 현재 시간")
    print("-" * 60)

    now_utc = get_current_utc()
    print(f"현재 UTC: {now_utc}")
    print(f"Timezone:  {now_utc.tz}")

    assert now_utc.tz is not None, "❌ Timezone 없음!"
    print("✅ 통과")


def test_4_dataframe_normalization():
    """테스트 4: DataFrame Timestamp 정규화"""
    print("\n[테스트 4] DataFrame Timestamp 정규화")
    print("-" * 60)

    df = pd.DataFrame({
        'timestamp': [1705334400000, 1705335300000],
        'close': [50000, 50100]
    })

    print("Before:")
    print(f"  dtype: {df['timestamp'].dtype}")
    print(f"  값: {df['timestamp'].iloc[0]}")

    # ✅ 새로운 방법: utc=True
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

    print("After:")
    print(f"  dtype: {df['timestamp'].dtype}")
    print(f"  값: {df['timestamp'].iloc[0]}")

    assert 'UTC' in str(df['timestamp'].dtype), f"❌ UTC timezone 없음: {df['timestamp'].dtype}"
    assert df['timestamp'].iloc[0].tz is not None, "❌ Timezone 없음!"

    print("✅ 통과")


def test_5_time_comparison():
    """테스트 5: 시간 비교"""
    print("\n[테스트 5] 시간 비교")
    print("-" * 60)

    t1 = to_utc_datetime(1705334400000, unit='ms')  # 12:00:00
    t2 = to_utc_datetime(1705335300000, unit='ms')  # 12:15:00

    diff_seconds = get_time_difference_seconds(t1, t2)

    print(f"시간 1: {t1}")
    print(f"시간 2: {t2}")
    print(f"차이:   {diff_seconds}초")

    assert diff_seconds == 900.0, f"❌ 시간 차이 오류: {diff_seconds}초 (예상: 900초)"

    print("✅ 통과")


def test_6_naive_vs_aware():
    """테스트 6: Naive vs Aware Datetime 비교"""
    print("\n[테스트 6] Naive vs Aware Datetime")
    print("-" * 60)

    # ❌ 기존 방법 (naive)
    df_naive = pd.DataFrame({'timestamp': [1705334400000]})
    df_naive['timestamp'] = pd.to_datetime(df_naive['timestamp'], unit='ms')

    # ✅ 새로운 방법 (aware)
    df_aware = pd.DataFrame({'timestamp': [1705334400000]})
    df_aware['timestamp'] = pd.to_datetime(df_aware['timestamp'], unit='ms', utc=True)

    print(f"Naive dtype: {df_naive['timestamp'].dtype}")
    print(f"Aware dtype: {df_aware['timestamp'].dtype}")

    naive_tz = df_naive['timestamp'].iloc[0].tz
    aware_tz = df_aware['timestamp'].iloc[0].tz

    print(f"Naive timezone: {naive_tz}")
    print(f"Aware timezone: {aware_tz}")

    assert naive_tz is None, "❌ Naive datetime이 timezone을 가지고 있음!"
    assert aware_tz is not None, "❌ Aware datetime이 timezone이 없음!"

    print("✅ 통과 (Naive는 timezone 없음, Aware는 UTC)")


def main():
    """모든 테스트 실행"""
    print("=" * 60)
    print("API Timezone 수정 검증")
    print("=" * 60)

    tests = [
        test_1_timestamp_conversion,
        test_2_local_time_conversion,
        test_3_current_time,
        test_4_dataframe_normalization,
        test_5_time_comparison,
        test_6_naive_vs_aware
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ 실패: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ 에러: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"결과: {passed}/{len(tests)} 통과, {failed} 실패")
    print("=" * 60)

    if failed == 0:
        print("\n✅ 모든 테스트 통과!")
        print("\n다음 단계:")
        print("1. python tools/fix_timezone.py (실제 파일 수정)")
        print("2. 거래소 API 테스트 (실제 데이터 확인)")
        return 0
    else:
        print("\n❌ 일부 테스트 실패")
        return 1


if __name__ == '__main__':
    sys.exit(main())
