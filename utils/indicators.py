"""
utils/indicators.py
통합 지표 계산 모듈 (Single Source of Truth)
- 모든 RSI, ATR, MACD, EMA 계산은 이 모듈을 통해 수행
- 백테스트와 실시간 매매에서 동일한 로직 사용 보장
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple

# Logging
import logging
logger = logging.getLogger(__name__)


def calculate_rsi(
    data: Union[np.ndarray, pd.Series], 
    period: int = 14,
    return_series: bool = False
) -> Union[float, pd.Series]:
    """
    RSI (Relative Strength Index) 계산
    
    Args:
        data: 종가 배열 (numpy array 또는 pandas Series)
        period: RSI 기간 (기본값: 14)
        return_series: True면 전체 Series 반환, False면 마지막 값만 반환
        
    Returns:
        float: 마지막 RSI 값 (return_series=False)
        pd.Series: 전체 RSI 시리즈 (return_series=True)
        
    Note:
        - SMA 방식 사용 (strategy_core.run_backtest와 동일)
        - 데이터가 부족하면 기본값 50 반환
    """
    if isinstance(data, np.ndarray):
        if len(data) < period + 1:
            return pd.Series([50.0] * len(data)) if return_series else 50.0
        
        # numpy 배열용 계산 (strategy_core.calculate_rsi 방식)
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(-deltas > 0, -deltas, 0)
        
        if return_series:
            # 전체 시리즈 계산
            series = pd.Series(data)
            delta = series.diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs.fillna(100)))
            return rsi.fillna(50)
        else:
            # 마지막 값만 계산
            avg_gain = np.mean(gains[-period:])
            avg_loss = np.mean(losses[-period:])
            if avg_loss == 0:
                return 100.0
            rs = avg_gain / avg_loss
            return 100 - (100 / (1 + rs))
    
    elif isinstance(data, pd.Series):
        # [OPT] 성능 최적 화 (긴 데이터 제한)
        if len(data) > 1000 and not return_series:
            data = data.tail(1000)

        if len(data) < period + 1:
            return pd.Series([50.0] * len(data), index=data.index) if return_series else 50.0
            
        delta = data.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # SMA 방식 (rolling mean)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # 0 나누기 방지
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs.fillna(100)))
        rsi = rsi.fillna(50)
        
        return rsi if return_series else float(rsi.iloc[-1])
    
    else:
        raise TypeError(f"data must be numpy.ndarray or pandas.Series, got {type(data)}")


def calculate_atr(
    df: pd.DataFrame, 
    period: int = 14,
    return_series: bool = False
) -> Union[float, pd.Series]:
    """
    ATR (Average True Range) 계산
    
    Args:
        df: OHLC 데이터프레임 (high, low, close 컬럼 필수)
        period: ATR 기간 (기본값: 14)
        return_series: True면 전체 Series 반환, False면 마지막 값만 반환
        
    Returns:
        float: 마지막 ATR 값 (return_series=False)
        pd.Series: 전체 ATR 시리즈 (return_series=True)
        
    Note:
        - SMA (Simple Moving Average) 방식 사용
        - 데이터가 부족하면 0 반환
    """
    if df is None or len(df) < period + 1:
        return pd.Series([0.0] * len(df) if df is not None else []) if return_series else 0.0
    
    highs = df['high'].values
    lows = df['low'].values
    closes = df['close'].values
    
    # True Range 계산
    # TR = max(H-L, |H-Pc|, |L-Pc|)
    high_low = highs - lows
    high_close = np.abs(highs - np.roll(closes, 1))
    low_close = np.abs(lows - np.roll(closes, 1))
    
    # 첫 번째 값 보정 (roll로 인한 잘못된 값)
    high_close[0] = high_low[0]
    low_close[0] = high_low[0]
    
    true_range = np.maximum(np.maximum(high_low, high_close), low_close)
    
    if return_series:
        atr = pd.Series(true_range, index=df.index).rolling(window=period).mean()
        return atr.fillna(0)
    else:
        return float(np.mean(true_range[-period:]))


def calculate_macd(
    data: Union[np.ndarray, pd.Series],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    return_all: bool = False
) -> Union[Tuple[float, float, float], Tuple[pd.Series, pd.Series, pd.Series]]:
    """
    MACD (Moving Average Convergence Divergence) 계산
    
    Args:
        data: 종가 데이터 (numpy array 또는 pandas Series)
        fast_period: Fast EMA 기간 (기본값: 12)
        slow_period: Slow EMA 기간 (기본값: 26)
        signal_period: Signal 기간 (기본값: 9)
        return_all: True면 전체 Series 반환
        
    Returns:
        Tuple[float, float, float]: (MACD, Signal, Histogram) 마지막 값
        Tuple[pd.Series, pd.Series, pd.Series]: (MACD, Signal, Histogram) 시리즈
        
    Note:
        - EWM (Exponential Weighted Moving Average) 방식 사용
    """
    if isinstance(data, np.ndarray):
        series = pd.Series(data)
    else:
        series = data
    
    # EMA 계산
    ema_fast = series.ewm(span=fast_period, adjust=False).mean()
    ema_slow = series.ewm(span=slow_period, adjust=False).mean()
    
    # MACD Line
    macd_line = ema_fast - ema_slow
    
    # Signal Line
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    
    # Histogram
    histogram = macd_line - signal_line
    
    if return_all:
        return macd_line, signal_line, histogram
    else:
        return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])


def calculate_ema(
    data: Union[np.ndarray, pd.Series],
    period: int = 20,
    return_series: bool = False
) -> Union[float, pd.Series]:
    """
    EMA (Exponential Moving Average) 계산
    
    Args:
        data: 종가 데이터 (numpy array 또는 pandas Series)
        period: EMA 기간 (기본값: 20)
        return_series: True면 전체 Series 반환
        
    Returns:
        float: 마지막 EMA 값 (return_series=False)
        pd.Series: 전체 EMA 시리즈 (return_series=True)
    """
    if isinstance(data, np.ndarray):
        series = pd.Series(data)
    else:
        series = data
    
    ema = series.ewm(span=period, adjust=False).mean()
    
    return ema if return_series else float(ema.iloc[-1])


def calculate_sma(
    data: Union[np.ndarray, pd.Series],
    period: int = 20,
    return_series: bool = False
) -> Union[float, pd.Series]:
    """
    SMA (Simple Moving Average) 계산
    
    Args:
        data: 종가 데이터 (numpy array 또는 pandas Series)
        period: SMA 기간 (기본값: 20)
        return_series: True면 전체 Series 반환
        
    Returns:
        float: 마지막 SMA 값 (return_series=False)
        pd.Series: 전체 SMA 시리즈 (return_series=True)
    """
    if isinstance(data, np.ndarray):
        series = pd.Series(data)
    else:
        series = data
    
    sma = series.rolling(window=period).mean()
    
    return sma if return_series else float(sma.iloc[-1])


def calculate_bollinger_bands(
    data: Union[np.ndarray, pd.Series],
    period: int = 20,
    std_dev: float = 2.0,
    return_series: bool = False
) -> Union[Tuple[float, float, float], Tuple[pd.Series, pd.Series, pd.Series]]:
    """
    Bollinger Bands 계산
    
    Args:
        data: 종가 데이터
        period: SMA 기간 (기본값: 20)
        std_dev: 표준편차 배수 (기본값: 2.0)
        return_series: True면 전체 Series 반환
        
    Returns:
        Tuple[float, float, float]: (Upper, Middle, Lower) 마지막 값
        Tuple[pd.Series, pd.Series, pd.Series]: (Upper, Middle, Lower) 시리즈
    """
    if isinstance(data, np.ndarray):
        series = pd.Series(data)
    else:
        series = data
    
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    if return_series:
        return upper, middle, lower
    else:
        return float(upper.iloc[-1]), float(middle.iloc[-1]), float(lower.iloc[-1])


def add_all_indicators(
    df: pd.DataFrame,
    rsi_period: int = 14,
    atr_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9
) -> pd.DataFrame:
    """
    데이터프레임에 모든 기본 지표 추가
    
    Args:
        df: OHLC 데이터프레임 (open, high, low, close, volume)
        rsi_period: RSI 기간
        atr_period: ATR 기간
        macd_fast: MACD Fast EMA 기간
        macd_slow: MACD Slow EMA 기간
        macd_signal: MACD Signal 기간
        
    Returns:
        pd.DataFrame: 지표가 추가된 데이터프레임
    """
    if df is None or df.empty:
        return df
    
    df = df.copy()
    
    if 'close' not in df.columns:
        return df
    
    # RSI
    df['rsi'] = calculate_rsi(df['close'], period=rsi_period, return_series=True)
    
    # ATR
    if all(c in df.columns for c in ['high', 'low', 'close']):
        df['atr'] = calculate_atr(df, period=atr_period, return_series=True)
    
    # MACD
    macd, signal, hist = calculate_macd(
        df['close'], 
        fast_period=macd_fast, 
        slow_period=macd_slow, 
        signal_period=macd_signal,
        return_all=True
    )
    df['macd'] = macd
    df['macd_signal'] = signal
    df['macd_hist'] = hist
    
    return df


# 하위 호환성을 위한 클래스 래퍼
class IndicatorCalculator:
    """
    레거시 코드 호환용 클래스 래퍼
    새 코드에서는 모듈 함수를 직접 사용하세요.
    """
    
    @staticmethod
    def calculate_rsi(data, period=14, return_series=False):
        return calculate_rsi(data, period, return_series)
    
    @staticmethod
    def calculate_atr(df, period=14, return_series=False):
        return calculate_atr(df, period, return_series)
    
    @staticmethod
    def calculate_macd(data, fast=12, slow=26, signal=9, return_all=False):
        return calculate_macd(data, fast, slow, signal, return_all)
    
    @staticmethod
    def calculate_ema(data, period=20, return_series=False):
        return calculate_ema(data, period, return_series)


if __name__ == '__main__':
    # 테스트 코드
    logger.info("=== Indicator Module Test ===\n")
    
    # 테스트 데이터 생성
    np.random.seed(42)
    test_data = 100 + np.cumsum(np.random.randn(100))
    test_df = pd.DataFrame({
        'open': test_data * 0.99,
        'high': test_data * 1.02,
        'low': test_data * 0.98,
        'close': test_data,
        'volume': np.random.randint(1000, 10000, 100)
    })
    
    # RSI 테스트
    rsi_val = calculate_rsi(test_data, period=14)
    rsi_series = calculate_rsi(pd.Series(test_data), period=14, return_series=True)
    logger.info(f"RSI (last): {rsi_val:.2f}")
    logger.info(f"RSI (series tail): {rsi_series.tail(3).tolist()}")
    
    # ATR 테스트
    atr_val = calculate_atr(test_df, period=14)
    atr_series = calculate_atr(test_df, period=14, return_series=True)
    logger.info(f"\nATR (last): {atr_val:.4f}")
    logger.info(f"ATR (series tail): {atr_series.tail(3).tolist()}")
    
    # MACD 테스트
    macd, signal, hist = calculate_macd(test_data)
    logger.info(f"\nMACD: {macd:.4f}, Signal: {signal:.4f}, Hist: {hist:.4f}")
    
    # EMA 테스트
    ema_val = calculate_ema(test_data, period=20)
    logger.info(f"\nEMA(20): {ema_val:.4f}")
    
    # add_all_indicators 테스트
    df_with_ind = add_all_indicators(test_df)
    logger.info(f"\nColumns after add_all_indicators: {df_with_ind.columns.tolist()}")
    logger.info(f"Last row indicators: RSI={df_with_ind['rsi'].iloc[-1]:.2f}, ATR={df_with_ind['atr'].iloc[-1]:.4f}")
    
    logger.info("\n✅ All tests passed!")
