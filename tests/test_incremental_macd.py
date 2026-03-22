"""
tests/test_incremental_macd.py
IncrementalMACD 클래스 단위 테스트 (v7.27)

검증 항목:
1. 배치 MACD vs 증분 MACD 정확도 (±1% 이내)
2. v7.27 파라미터 (6/18/7) 정확성
3. 성능 (73배 이상 빠름 예상)
4. 엣지 케이스 (초기값, 단일 값, 리셋)
"""
import sys
from pathlib import Path
import time

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import numpy as np
import pandas as pd
from utils.incremental_indicators import IncrementalMACD
from utils.indicators import calculate_macd


def test_incremental_vs_batch_accuracy():
    """테스트 1: 배치 MACD vs 증분 MACD 정확도"""
    print("=" * 80)
    print("테스트 1: 배치 MACD vs 증분 MACD 정확도 (±1% 이내)")
    print("=" * 80)

    # 테스트 데이터 생성 (1000개 랜덤 가격)
    np.random.seed(42)
    prices = np.random.randn(1000).cumsum() + 100
    prices = np.maximum(prices, 50)  # 최소 50

    df = pd.DataFrame({'close': prices})

    # 1. 배치 MACD 계산 (v7.27 파라미터: 6/18/7)
    macd_line, signal_line, histogram = calculate_macd(
        df['close'],
        fast_period=6,
        slow_period=18,
        signal_period=7,
        return_all=True
    )
    df_batch = pd.DataFrame({
        'macd': macd_line,
        'macd_signal': signal_line,
        'macd_histogram': histogram
    })

    # 2. 증분 MACD 계산
    macd_tracker = IncrementalMACD(fast=6, slow=18, signal=7)
    incremental_results = []

    for price in prices:
        result = macd_tracker.update(price)
        incremental_results.append(result)

    # DataFrame으로 변환
    df_incremental = pd.DataFrame(incremental_results)

    # 3. 정확도 비교 (마지막 100개만, 워밍업 제외)
    compare_start = 100
    macd_batch = np.asarray(df_batch['macd'].iloc[compare_start:].values)
    macd_incr = np.asarray(df_incremental['macd_line'].iloc[compare_start:].values)

    signal_batch = np.asarray(df_batch['macd_signal'].iloc[compare_start:].values)
    signal_incr = np.asarray(df_incremental['signal_line'].iloc[compare_start:].values)

    histogram_batch = np.asarray(df_batch['macd_histogram'].iloc[compare_start:].values)
    histogram_incr = np.asarray(df_incremental['histogram'].iloc[compare_start:].values)

    # 상대 오차 계산 (%)
    macd_error = np.abs((macd_incr - macd_batch) / (np.abs(macd_batch) + 1e-10)) * 100
    signal_error = np.abs((signal_incr - signal_batch) / (np.abs(signal_batch) + 1e-10)) * 100
    histogram_error = np.abs((histogram_incr - histogram_batch) / (np.abs(histogram_batch) + 1e-10)) * 100

    macd_mean_error = np.mean(macd_error)
    signal_mean_error = np.mean(signal_error)
    histogram_mean_error = np.mean(histogram_error)

    print(f"\n정확도 (평균 상대 오차):")
    print(f"  MACD Line:   {macd_mean_error:.4f}% (목표: <1%)")
    print(f"  Signal Line: {signal_mean_error:.4f}% (목표: <1%)")
    print(f"  Histogram:   {histogram_mean_error:.4f}% (목표: <1%)")

    # 검증
    assert macd_mean_error < 1.0, f"MACD Line 오차 {macd_mean_error:.4f}% > 1%"
    assert signal_mean_error < 1.0, f"Signal Line 오차 {signal_mean_error:.4f}% > 1%"
    assert histogram_mean_error < 1.0, f"Histogram 오차 {histogram_mean_error:.4f}% > 1%"

    print("\n[OK] 정확도 테스트 통과 (±1% 이내)")


def test_v727_parameters():
    """테스트 2: v7.27 파라미터 (6/18/7) 정확성"""
    print("\n" + "=" * 80)
    print("테스트 2: v7.27 파라미터 (6/18/7) 정확성")
    print("=" * 80)

    # 단순 상승 추세 데이터
    prices = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110]

    # IncrementalMACD (6/18/7)
    macd = IncrementalMACD(fast=6, slow=18, signal=7)

    results = []
    for price in prices:
        result = macd.update(price)
        results.append(result)

    # 마지막 값 확인 (상승 추세에서 Histogram > 0 예상)
    last_result = results[-1]
    print(f"\n마지막 MACD 값 (상승 추세):")
    print(f"  MACD Line:   {last_result['macd_line']:.4f}")
    print(f"  Signal Line: {last_result['signal_line']:.4f}")
    print(f"  Histogram:   {last_result['histogram']:.4f}")

    # 검증: 상승 추세에서 Histogram > 0
    assert last_result['histogram'] > 0, f"상승 추세에서 Histogram이 음수: {last_result['histogram']:.4f}"

    print("\n[OK] v7.27 파라미터 테스트 통과")


def test_performance():
    """테스트 3: 성능 (73배 이상 빠름 예상)"""
    print("\n" + "=" * 80)
    print("테스트 3: 성능 비교 (배치 vs 증분)")
    print("=" * 80)

    # 테스트 데이터 (10,000개)
    np.random.seed(42)
    prices = np.random.randn(10000).cumsum() + 100
    prices = np.maximum(prices, 50)

    df = pd.DataFrame({'close': prices})

    # 1. 배치 MACD (10,000번 재계산)
    start = time.perf_counter()
    for i in range(100, len(prices)):
        df_window = df.iloc[:i+1].copy()
        _ = calculate_macd(df_window['close'], fast_period=6, slow_period=18, signal_period=7, return_all=True)
    batch_time = time.perf_counter() - start

    # 2. 증분 MACD (10,000번 업데이트)
    start = time.perf_counter()
    macd = IncrementalMACD(fast=6, slow=18, signal=7)
    for price in prices:
        _ = macd.update(price)
    incremental_time = time.perf_counter() - start

    speedup = batch_time / incremental_time

    print(f"\n성능 (9,900번 업데이트):")
    print(f"  배치 MACD:   {batch_time:.4f}초")
    print(f"  증분 MACD:   {incremental_time:.4f}초")
    print(f"  속도 향상:   {speedup:.1f}배")

    # 검증: 최소 50배 이상 빠름 (목표 73배)
    assert speedup > 50, f"속도 향상 {speedup:.1f}배 < 50배"

    print(f"\n[OK] 성능 테스트 통과 ({speedup:.1f}배 빠름)")


def test_edge_cases():
    """테스트 4: 엣지 케이스"""
    print("\n" + "=" * 80)
    print("테스트 4: 엣지 케이스")
    print("=" * 80)

    # Case 1: 초기값 (첫 업데이트)
    macd = IncrementalMACD(fast=6, slow=18, signal=7)
    result = macd.update(100.0)
    assert result['macd_line'] == 0.0, "초기 MACD Line은 0"
    assert result['signal_line'] == 0.0, "초기 Signal Line은 0"
    assert result['histogram'] == 0.0, "초기 Histogram은 0"
    print("  [OK] 초기값 테스트")

    # Case 2: 단일 값 반복 (변동 없음)
    macd = IncrementalMACD(fast=6, slow=18, signal=7)
    for _ in range(50):
        result = macd.update(100.0)
    assert abs(result['macd_line']) < 1e-10, "변동 없으면 MACD Line ≈ 0"
    assert abs(result['histogram']) < 1e-10, "변동 없으면 Histogram ≈ 0"
    print("  [OK] 단일 값 반복 테스트")

    # Case 3: 리셋 후 재시작
    macd = IncrementalMACD(fast=6, slow=18, signal=7)
    macd.update(100.0)
    macd.update(101.0)
    macd.reset()
    result = macd.update(100.0)
    assert result['macd_line'] == 0.0, "리셋 후 초기 MACD Line은 0"
    print("  [OK] 리셋 테스트")

    # Case 4: get_current() 동작
    macd = IncrementalMACD(fast=6, slow=18, signal=7)
    assert macd.get_current() is None, "업데이트 전 get_current()는 None"
    macd.update(100.0)
    current = macd.get_current()
    assert current is not None, "업데이트 후 get_current()는 dict"
    assert 'macd_line' in current, "dict에 macd_line 포함"
    print("  [OK] get_current() 테스트")

    print("\n[OK] 엣지 케이스 테스트 통과")


def test_parameter_validation():
    """테스트 5: 파라미터 검증"""
    print("\n" + "=" * 80)
    print("테스트 5: 파라미터 검증")
    print("=" * 80)

    # Case 1: fast >= slow (오류)
    try:
        IncrementalMACD(fast=18, slow=6, signal=7)
        assert False, "fast >= slow는 ValueError 발생해야 함"
    except ValueError as e:
        print(f"  [OK] fast >= slow 검증: {e}")

    # Case 2: 음수 기간 (오류)
    try:
        IncrementalMACD(fast=-6, slow=18, signal=7)
        assert False, "음수 기간은 ValueError 발생해야 함"
    except ValueError as e:
        print(f"  [OK] 음수 기간 검증: {e}")

    # Case 3: 0 기간 (오류)
    try:
        IncrementalMACD(fast=0, slow=18, signal=7)
        assert False, "0 기간은 ValueError 발생해야 함"
    except ValueError as e:
        print(f"  [OK] 0 기간 검증: {e}")

    print("\n[OK] 파라미터 검증 테스트 통과")


if __name__ == '__main__':
    print("=" * 80)
    print("IncrementalMACD 단위 테스트 (v7.27)")
    print("=" * 80)

    try:
        test_incremental_vs_batch_accuracy()
        test_v727_parameters()
        test_performance()
        test_edge_cases()
        test_parameter_validation()

        print("\n" + "=" * 80)
        print("[SUCCESS] 모든 테스트 통과 (5/5)")
        print("=" * 80)

    except AssertionError as e:
        print(f"\n[FAIL] 테스트 실패: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] 예외 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
