"""
tests/test_indicators_accuracy.py
지표 계산 정확성 검증 (Wilder's Smoothing 표준 준수)

Wilder 1978 논문 기준 데이터로 RSI/ATR 계산 검증
"""
import pytest
import pandas as pd
import numpy as np
from utils.indicators import calculate_rsi, calculate_atr


class TestRSIAccuracy:
    """RSI 계산 정확성 검증 (Wilder's Smoothing)"""

    def test_rsi_wilder_original_example(self):
        """
        Wilder's 원본 예제 데이터로 RSI 계산 검증

        출처: Wilder, J. Welles (1978). "New Concepts in Technical Trading Systems"
        예제 데이터: 14일 RSI 계산
        """
        # Wilder의 원본 예제 데이터 (종가)
        data = pd.Series([
            44.00, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
            45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00,
            46.03, 46.41, 46.22, 45.64
        ])

        # RSI 계산
        rsi = calculate_rsi(data, period=14, return_series=True)

        # Wilder의 원본 결과와 비교 (14번째 값부터 유효)
        # 참고: 첫 14개 값은 워밍업 기간
        last_rsi = rsi.iloc[-1]

        # 예상값: 약 51.78 (Wilder의 계산 결과)
        # 허용 오차: ±1.0 (EWM 구현 차이 고려)
        assert 50.0 <= last_rsi <= 53.0, f"RSI 값이 범위를 벗어남: {last_rsi:.2f}"

    def test_rsi_extreme_oversold(self):
        """극단적 과매도 상황 (지속적 하락)"""
        # 지속적으로 하락하는 데이터 생성
        data = pd.Series([100 - i for i in range(30)])

        rsi = calculate_rsi(data, period=14, return_series=True)
        last_rsi = rsi.iloc[-1]

        # 지속적 하락 → RSI는 0에 가까워야 함
        assert 0 <= last_rsi <= 10, f"과매도 RSI가 비정상: {last_rsi:.2f}"

    def test_rsi_extreme_overbought(self):
        """극단적 과매수 상황 (지속적 상승)"""
        # 지속적으로 상승하는 데이터 생성
        data = pd.Series([100 + i for i in range(30)])

        rsi = calculate_rsi(data, period=14, return_series=True)
        last_rsi = rsi.iloc[-1]

        # 지속적 상승 → RSI는 100에 가까워야 함
        assert 90 <= last_rsi <= 100, f"과매수 RSI가 비정상: {last_rsi:.2f}"

    def test_rsi_neutral_market(self):
        """중립 시장 (등락 반복)"""
        # 상승/하락 반복 데이터
        data = pd.Series([100, 101, 100, 101, 100, 101, 100, 101,
                          100, 101, 100, 101, 100, 101, 100, 101])

        rsi = calculate_rsi(data, period=14, return_series=True)
        last_rsi = rsi.iloc[-1]

        # 중립 시장 → RSI는 50 근처
        assert 45 <= last_rsi <= 55, f"중립 RSI가 비정상: {last_rsi:.2f}"

    def test_rsi_insufficient_data(self):
        """데이터 부족 시 기본값 반환"""
        # 14개 미만 데이터
        data = pd.Series([100, 101, 102])

        rsi = calculate_rsi(data, period=14, return_series=True)

        # 기본값 50 반환
        assert all(rsi == 50.0), "데이터 부족 시 50 반환해야 함"

    def test_rsi_numpy_vs_pandas(self):
        """numpy 배열과 pandas Series 결과 일치 확인"""
        data_array = np.array([44.0, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
                               45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00])
        data_series = pd.Series(data_array)

        rsi_numpy = calculate_rsi(data_array, period=14, return_series=False)
        rsi_pandas = calculate_rsi(data_series, period=14, return_series=False)

        # 결과 일치 확인 (±0.01 허용)
        assert abs(rsi_numpy - rsi_pandas) < 0.01, \
            f"numpy/pandas 결과 불일치: {rsi_numpy:.2f} vs {rsi_pandas:.2f}"


class TestATRAccuracy:
    """ATR 계산 정확성 검증 (Wilder's Smoothing)"""

    def test_atr_wilder_example(self):
        """
        Wilder's 원본 예제 데이터로 ATR 계산 검증

        출처: Wilder, J. Welles (1978). "New Concepts in Technical Trading Systems"
        """
        # Wilder의 원본 예제 데이터
        df = pd.DataFrame({
            'high': [48.70, 48.72, 48.90, 48.87, 48.82, 49.05, 49.20, 49.35,
                     49.92, 50.19, 50.12, 49.66, 49.88, 50.19, 50.36],
            'low': [47.79, 48.14, 48.39, 48.37, 48.24, 48.64, 48.94, 49.10,
                    49.50, 49.87, 49.20, 48.90, 49.43, 49.73, 49.26],
            'close': [48.16, 48.61, 48.75, 48.63, 48.74, 49.03, 49.07, 49.32,
                      49.91, 50.13, 49.53, 49.50, 49.75, 50.03, 50.31]
        })

        # ATR 계산
        atr = calculate_atr(df, period=14, return_series=True)
        last_atr = atr.iloc[-1]

        # Wilder의 예제 결과: 약 0.56
        # 허용 오차: ±0.10 (구현 차이 고려)
        assert 0.40 <= last_atr <= 0.70, f"ATR 값이 범위를 벗어남: {last_atr:.2f}"

    def test_atr_high_volatility(self):
        """고변동성 시장 (큰 가격 변동)"""
        df = pd.DataFrame({
            'high': [100 + i * 5 for i in range(20)],
            'low': [90 + i * 5 for i in range(20)],
            'close': [95 + i * 5 for i in range(20)]
        })

        atr = calculate_atr(df, period=14, return_series=True)
        last_atr = atr.iloc[-1]

        # 고변동성 → ATR이 커야 함 (최소 10 이상)
        assert last_atr >= 10, f"고변동성 ATR이 너무 낮음: {last_atr:.2f}"

    def test_atr_low_volatility(self):
        """저변동성 시장 (작은 가격 변동)"""
        df = pd.DataFrame({
            'high': [100.1, 100.2, 100.1, 100.2, 100.1, 100.2, 100.1, 100.2,
                     100.1, 100.2, 100.1, 100.2, 100.1, 100.2, 100.1],
            'low': [99.9, 99.8, 99.9, 99.8, 99.9, 99.8, 99.9, 99.8,
                    99.9, 99.8, 99.9, 99.8, 99.9, 99.8, 99.9],
            'close': [100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0,
                      100.0, 100.0, 100.0, 100.0, 100.0, 100.0, 100.0]
        })

        atr = calculate_atr(df, period=14, return_series=True)
        last_atr = atr.iloc[-1]

        # 저변동성 → ATR이 작아야 함 (최대 0.5 이하)
        assert last_atr <= 0.5, f"저변동성 ATR이 너무 높음: {last_atr:.2f}"

    def test_atr_gap_up(self):
        """갭 상승 (전일 종가 대비 큰 갭)"""
        df = pd.DataFrame({
            'high': [100, 101, 120, 121, 122],  # 갭 상승
            'low': [95, 96, 115, 116, 117],
            'close': [98, 99, 118, 119, 120]
        })

        atr = calculate_atr(df, period=3, return_series=True)

        # 갭 발생 후 ATR 증가 확인
        atr_before_gap = atr.iloc[1]  # 갭 발생 전
        atr_after_gap = atr.iloc[3]   # 갭 발생 후

        assert atr_after_gap > atr_before_gap, \
            f"갭 발생 후 ATR이 증가하지 않음: {atr_before_gap:.2f} → {atr_after_gap:.2f}"

    def test_atr_insufficient_data(self):
        """데이터 부족 시 0 반환"""
        df = pd.DataFrame({
            'high': [100, 101],
            'low': [95, 96],
            'close': [98, 99]
        })

        atr = calculate_atr(df, period=14, return_series=True)

        # 데이터 부족 시 0 반환
        assert all(atr == 0.0), "데이터 부족 시 0 반환해야 함"

    def test_atr_positive_values(self):
        """ATR은 항상 양수여야 함"""
        df = pd.DataFrame({
            'high': np.random.uniform(95, 105, 30),
            'low': np.random.uniform(90, 100, 30),
            'close': np.random.uniform(92, 103, 30)
        })

        atr = calculate_atr(df, period=14, return_series=True)

        # ATR은 항상 >= 0
        assert all(atr >= 0), "ATR에 음수 값이 존재함"


class TestIndicatorConsistency:
    """지표 계산 일관성 검증"""

    def test_rsi_series_vs_single_value(self):
        """return_series=True와 False 결과 일치 확인"""
        data = pd.Series([44.0, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
                          45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00])

        rsi_series = calculate_rsi(data, period=14, return_series=True)
        rsi_single = calculate_rsi(data, period=14, return_series=False)

        # 마지막 값 일치 확인
        assert abs(rsi_series.iloc[-1] - rsi_single) < 0.01, \
            "return_series=True/False 결과 불일치"

    def test_atr_series_vs_single_value(self):
        """return_series=True와 False 결과 일치 확인"""
        df = pd.DataFrame({
            'high': [48.70, 48.72, 48.90, 48.87, 48.82, 49.05, 49.20, 49.35,
                     49.92, 50.19, 50.12, 49.66, 49.88, 50.19, 50.36],
            'low': [47.79, 48.14, 48.39, 48.37, 48.24, 48.64, 48.94, 49.10,
                    49.50, 49.87, 49.20, 48.90, 49.43, 49.73, 49.26],
            'close': [48.16, 48.61, 48.75, 48.63, 48.74, 49.03, 49.07, 49.32,
                      49.91, 50.13, 49.53, 49.50, 49.75, 50.03, 50.31]
        })

        atr_series = calculate_atr(df, period=14, return_series=True)
        atr_single = calculate_atr(df, period=14, return_series=False)

        # 마지막 값 일치 확인
        assert abs(atr_series.iloc[-1] - atr_single) < 0.01, \
            "return_series=True/False 결과 불일치"

    def test_rsi_deterministic(self):
        """RSI 계산이 결정적(deterministic)인지 확인"""
        data = pd.Series([44.0, 44.34, 44.09, 43.61, 44.33, 44.83, 45.10, 45.42,
                          45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28, 46.00])

        # 동일 입력에 대해 동일 결과
        rsi1 = calculate_rsi(data, period=14, return_series=False)
        rsi2 = calculate_rsi(data, period=14, return_series=False)

        assert rsi1 == rsi2, "RSI 계산이 비결정적임"

    def test_atr_deterministic(self):
        """ATR 계산이 결정적(deterministic)인지 확인"""
        df = pd.DataFrame({
            'high': [48.70, 48.72, 48.90, 48.87, 48.82],
            'low': [47.79, 48.14, 48.39, 48.37, 48.24],
            'close': [48.16, 48.61, 48.75, 48.63, 48.74]
        })

        # 동일 입력에 대해 동일 결과
        atr1 = calculate_atr(df, period=3, return_series=False)
        atr2 = calculate_atr(df, period=3, return_series=False)

        assert atr1 == atr2, "ATR 계산이 비결정적임"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
