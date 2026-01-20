"""
utils/incremental_indicators.py
실시간 거래용 증분 지표 계산 (O(1) 복잡도)

- IncrementalEMA: EMA 증분 업데이트
- IncrementalRSI: RSI 증분 업데이트 (Wilder's Smoothing)
- IncrementalATR: ATR 증분 업데이트 (Wilder's Smoothing)
- IncrementalMACD: MACD 증분 업데이트 (v7.27)

사용 사례:
- WebSocket 실시간 데이터 처리
- 1개 캔들 추가 시 전체 재계산 불필요
- 95% 이상 속도 향상
"""

import numpy as np
from typing import Optional


class IncrementalEMA:
    """
    증분 EMA (Exponential Moving Average) 계산기

    새로운 값이 추가될 때마다 O(1) 시간에 EMA 업데이트
    전체 재계산 불필요 (메모리 효율적)

    Example:
        >>> ema = IncrementalEMA(period=20)
        >>> for price in prices:
        ...     current_ema = ema.update(price)
    """

    def __init__(self, period: int):
        """
        Args:
            period: EMA 기간 (예: 20)
        """
        if period <= 0:
            raise ValueError(f"period must be positive, got {period}")

        self.period = period
        self.alpha = 2 / (period + 1)  # EMA 가중치
        self.current_ema: Optional[float] = None

    def update(self, new_value: float) -> float:
        """
        새 값으로 EMA 업데이트 (O(1) 복잡도)

        Args:
            new_value: 새로운 데이터 값 (예: 종가)

        Returns:
            float: 업데이트된 EMA 값

        Note:
            첫 번째 값은 그대로 사용 (초기화)
        """
        if self.current_ema is None:
            self.current_ema = new_value
        else:
            self.current_ema = self.alpha * new_value + (1 - self.alpha) * self.current_ema

        return self.current_ema

    def get_current(self) -> Optional[float]:
        """현재 EMA 값 반환"""
        return self.current_ema

    def reset(self) -> None:
        """상태 초기화 (다음 계산 시작 시 첫 값부터)"""
        self.current_ema = None

    def __repr__(self) -> str:
        return f"IncrementalEMA(period={self.period}, current={self.current_ema:.4f if self.current_ema else 'None'})"


class IncrementalRSI:
    """
    증분 RSI (Relative Strength Index) 계산기 (Wilder's Smoothing)

    새로운 종가가 추가될 때마다 O(1) 시간에 RSI 업데이트
    Wilder's Smoothing 방식 사용 (금융 산업 표준)

    Example:
        >>> rsi = IncrementalRSI(period=14)
        >>> for close in closes:
        ...     current_rsi = rsi.update(close)
    """

    def __init__(self, period: int = 14):
        """
        Args:
            period: RSI 기간 (기본값: 14)
        """
        if period <= 0:
            raise ValueError(f"period must be positive, got {period}")

        self.period = period
        self.alpha = 1 / period  # Wilder's alpha (= 1/n)
        self.avg_gain: Optional[float] = None
        self.avg_loss: Optional[float] = None
        self.prev_close: Optional[float] = None

    def update(self, close: float) -> float:
        """
        새 종가로 RSI 업데이트 (O(1) 복잡도)

        Args:
            close: 새로운 종가

        Returns:
            float: 업데이트된 RSI 값 (0-100)

        Note:
            - 첫 번째 값은 기본값 50 반환
            - Wilder's Smoothing: avg = (prev_avg * (n-1) + new) / n
        """
        if self.prev_close is None:
            self.prev_close = close
            return 50.0  # 초기값

        # Gain/Loss 계산
        change = close - self.prev_close
        gain = max(change, 0.0)
        loss = max(-change, 0.0)

        # Wilder's Smoothing
        if self.avg_gain is None or self.avg_loss is None:
            # 첫 gain/loss는 그대로 사용
            self.avg_gain = gain
            self.avg_loss = loss
        else:
            # Wilder's formula: avg = (prev_avg * (n-1) + new) / n
            self.avg_gain = (self.avg_gain * (self.period - 1) + gain) / self.period
            self.avg_loss = (self.avg_loss * (self.period - 1) + loss) / self.period

        # RSI 계산 (avg_gain과 avg_loss는 이제 None이 아님)
        assert self.avg_gain is not None and self.avg_loss is not None
        if self.avg_loss == 0:
            rsi = 100.0  # 모든 상승 → RSI 100
        else:
            rs = self.avg_gain / self.avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

        self.prev_close = close
        return rsi

    def get_current(self) -> Optional[float]:
        """현재 RSI 값 반환 (계산되지 않았으면 None)"""
        if self.avg_gain is None or self.avg_loss is None:
            return None

        if self.avg_loss == 0:
            return 100.0
        else:
            rs = self.avg_gain / self.avg_loss
            return 100.0 - (100.0 / (1.0 + rs))

    def reset(self) -> None:
        """상태 초기화"""
        self.avg_gain = None
        self.avg_loss = None
        self.prev_close = None

    def __repr__(self) -> str:
        current = self.get_current()
        return f"IncrementalRSI(period={self.period}, current={current:.2f if current else 'None'})"


class IncrementalATR:
    """
    증분 ATR (Average True Range) 계산기 (Wilder's Smoothing)

    새로운 OHLC 캔들이 추가될 때마다 O(1) 시간에 ATR 업데이트
    Wilder's Smoothing 방식 사용 (금융 산업 표준)

    Example:
        >>> atr = IncrementalATR(period=14)
        >>> for candle in candles:
        ...     current_atr = atr.update(
        ...         high=candle['high'],
        ...         low=candle['low'],
        ...         close=candle['close']
        ...     )
    """

    def __init__(self, period: int = 14):
        """
        Args:
            period: ATR 기간 (기본값: 14)
        """
        if period <= 0:
            raise ValueError(f"period must be positive, got {period}")

        self.period = period
        self.alpha = 1 / period  # Wilder's alpha
        self.current_atr: Optional[float] = None
        self.prev_close: Optional[float] = None

    def update(self, high: float, low: float, close: float) -> float:
        """
        새 캔들로 ATR 업데이트 (O(1) 복잡도)

        Args:
            high: 고가
            low: 저가
            close: 종가

        Returns:
            float: 업데이트된 ATR 값

        Note:
            - True Range = max(H-L, |H-Pc|, |L-Pc|)
            - Wilder's Smoothing: atr = (prev_atr * (n-1) + tr) / n
        """
        # True Range 계산
        if self.prev_close is None:
            # 첫 번째 캔들: TR = H - L
            tr = high - low
        else:
            # TR = max(H-L, |H-Pc|, |L-Pc|)
            tr = max(
                high - low,
                abs(high - self.prev_close),
                abs(low - self.prev_close)
            )

        # Wilder's Smoothing
        if self.current_atr is None:
            # 첫 번째 TR은 그대로 사용
            self.current_atr = tr
        else:
            # Wilder's formula: atr = (prev_atr * (n-1) + tr) / n
            self.current_atr = (self.current_atr * (self.period - 1) + tr) / self.period

        self.prev_close = close
        return self.current_atr

    def get_current(self) -> Optional[float]:
        """현재 ATR 값 반환"""
        return self.current_atr

    def reset(self) -> None:
        """상태 초기화"""
        self.current_atr = None
        self.prev_close = None

    def __repr__(self) -> str:
        return f"IncrementalATR(period={self.period}, current={self.current_atr:.4f if self.current_atr else 'None'})"


class IncrementalMACD:
    """
    증분 MACD (Moving Average Convergence Divergence) 계산기 (v7.27)

    새로운 종가가 추가될 때마다 O(1) 시간에 MACD 업데이트
    EMA 기반 계산 (Fast, Slow, Signal)

    MACD Line = EMA(fast) - EMA(slow)
    Signal Line = EMA(MACD Line, signal_period)
    Histogram = MACD Line - Signal Line

    Example:
        >>> macd = IncrementalMACD(fast=6, slow=18, signal=7)
        >>> for close in closes:
        ...     result = macd.update(close)
        ...     print(f"Histogram: {result['histogram']:.4f}")
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        """
        Args:
            fast: 빠른 EMA 기간 (기본값: 12, v7.27: 6)
            slow: 느린 EMA 기간 (기본값: 26, v7.27: 18)
            signal: Signal Line EMA 기간 (기본값: 9, v7.27: 7)
        """
        if fast <= 0 or slow <= 0 or signal <= 0:
            raise ValueError(f"All periods must be positive, got fast={fast}, slow={slow}, signal={signal}")
        if fast >= slow:
            raise ValueError(f"fast period ({fast}) must be less than slow period ({slow})")

        self.fast = fast
        self.slow = slow
        self.signal = signal

        # EMA 트래커 생성
        self.ema_fast = IncrementalEMA(period=fast)
        self.ema_slow = IncrementalEMA(period=slow)
        self.ema_signal = IncrementalEMA(period=signal)

        # 현재 MACD 값 저장
        self.current_macd: Optional[float] = None
        self.current_signal: Optional[float] = None
        self.current_histogram: Optional[float] = None

    def update(self, close: float) -> dict:
        """
        새 종가로 MACD 업데이트 (O(1) 복잡도)

        Args:
            close: 새로운 종가

        Returns:
            dict: {
                'macd_line': MACD Line 값,
                'signal_line': Signal Line 값,
                'histogram': Histogram 값
            }

        Note:
            - Fast/Slow EMA 계산 후 MACD Line 도출
            - MACD Line으로 Signal Line 계산
            - Histogram = MACD - Signal
        """
        # 1. Fast/Slow EMA 업데이트
        ema_fast_value = self.ema_fast.update(close)
        ema_slow_value = self.ema_slow.update(close)

        # 2. MACD Line 계산
        self.current_macd = ema_fast_value - ema_slow_value

        # 3. Signal Line 계산 (MACD Line의 EMA)
        self.current_signal = self.ema_signal.update(self.current_macd)

        # 4. Histogram 계산
        self.current_histogram = self.current_macd - self.current_signal

        return {
            'macd_line': self.current_macd,
            'signal_line': self.current_signal,
            'histogram': self.current_histogram
        }

    def get_current(self) -> Optional[dict]:
        """현재 MACD 값 반환 (계산되지 않았으면 None)"""
        if self.current_macd is None or self.current_signal is None or self.current_histogram is None:
            return None

        return {
            'macd_line': self.current_macd,
            'signal_line': self.current_signal,
            'histogram': self.current_histogram
        }

    def reset(self) -> None:
        """상태 초기화"""
        self.ema_fast.reset()
        self.ema_slow.reset()
        self.ema_signal.reset()
        self.current_macd = None
        self.current_signal = None
        self.current_histogram = None

    def __repr__(self) -> str:
        hist = f"{self.current_histogram:.4f}" if self.current_histogram is not None else "None"
        return f"IncrementalMACD(fast={self.fast}, slow={self.slow}, signal={self.signal}, histogram={hist})"


# 편의 함수들
def create_rsi_tracker(period: int = 14) -> IncrementalRSI:
    """RSI 트래커 생성 (편의 함수)"""
    return IncrementalRSI(period=period)


def create_atr_tracker(period: int = 14) -> IncrementalATR:
    """ATR 트래커 생성 (편의 함수)"""
    return IncrementalATR(period=period)


def create_ema_tracker(period: int = 20) -> IncrementalEMA:
    """EMA 트래커 생성 (편의 함수)"""
    return IncrementalEMA(period=period)


def create_macd_tracker(fast: int = 12, slow: int = 26, signal: int = 9) -> IncrementalMACD:
    """MACD 트래커 생성 (편의 함수)

    Args:
        fast: 빠른 EMA 기간 (기본값: 12, v7.27: 6)
        slow: 느린 EMA 기간 (기본값: 26, v7.27: 18)
        signal: Signal Line EMA 기간 (기본값: 9, v7.27: 7)
    """
    return IncrementalMACD(fast=fast, slow=slow, signal=signal)


if __name__ == '__main__':
    # 테스트 코드
    print("=== Incremental Indicators Test ===\n")

    # 테스트 데이터
    test_closes = [100, 101, 102, 101, 103, 104, 102, 105, 107, 106]
    test_candles = [
        {'high': 102, 'low': 98, 'close': 100},
        {'high': 103, 'low': 99, 'close': 101},
        {'high': 104, 'low': 100, 'close': 102},
        {'high': 103, 'low': 99, 'close': 101},
        {'high': 105, 'low': 101, 'close': 103},
    ]

    # EMA 테스트
    print("1. IncrementalEMA Test")
    ema = IncrementalEMA(period=3)
    for i, close in enumerate(test_closes[:5]):
        current = ema.update(close)
        print(f"  Close: {close}, EMA: {current:.2f}")

    # RSI 테스트
    print("\n2. IncrementalRSI Test")
    rsi = IncrementalRSI(period=3)
    for i, close in enumerate(test_closes):
        current = rsi.update(close)
        print(f"  Close: {close}, RSI: {current:.2f}")

    # ATR 테스트
    print("\n3. IncrementalATR Test")
    atr = IncrementalATR(period=3)
    for candle in test_candles:
        current = atr.update(**candle)
        print(f"  H:{candle['high']}, L:{candle['low']}, C:{candle['close']}, ATR: {current:.2f}")

    # MACD 테스트
    print("\n4. IncrementalMACD Test (v7.27 파라미터)")
    macd = IncrementalMACD(fast=6, slow=18, signal=7)
    for i, close in enumerate(test_closes):
        result = macd.update(close)
        print(f"  Close: {close}, MACD: {result['macd_line']:.4f}, Signal: {result['signal_line']:.4f}, Histogram: {result['histogram']:.4f}")

    print("\n=== All Tests Completed ===")
