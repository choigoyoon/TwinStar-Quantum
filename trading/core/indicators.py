"""
지표 계산 모듈
=============

기술적 지표 계산 함수 모음

핵심 지표:
- RSI: 상대강도지수
- MACD: 이동평균수렴확산
- EMA: 지수이동평균
- ATR: 평균진폭
- Bollinger Bands: 볼린저 밴드

v2.0 업데이트: trading/core/indicators.py 통합
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# SSOT: utils.indicators 모듈 사용 (Phase 1)
# calculate_rsi, calculate_atr는 utils.indicators에서 직접 import


@dataclass
class IndicatorSet:
    """
    지표 세트 데이터 클래스
    
    Attributes:
        rsi: RSI 값
        macd: MACD 값
        macd_signal: MACD 시그널 값
        macd_hist: MACD 히스토그램
        ema: EMA 값
        atr: ATR 값
        bb_upper: 볼린저 상단
        bb_middle: 볼린저 중간
        bb_lower: 볼린저 하단
    """
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_hist: Optional[float] = None
    ema: Optional[float] = None
    atr: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            'rsi': self.rsi,
            'macd': self.macd,
            'macd_signal': self.macd_signal,
            'macd_hist': self.macd_hist,
            'ema': self.ema,
            'atr': self.atr,
            'bb_upper': self.bb_upper,
            'bb_middle': self.bb_middle,
            'bb_lower': self.bb_lower,
        }


# calculate_rsi() 삭제 → utils.indicators 사용 (SSOT)


def calculate_ema(close: pd.Series, period: int = 20) -> pd.Series:
    """
    EMA (Exponential Moving Average) 계산
    
    Args:
        close: 종가 시리즈
        period: EMA 기간
    
    Returns:
        EMA 값 시리즈
    """
    return close.ewm(span=period, adjust=False).mean()


def calculate_sma(close: pd.Series, period: int = 20) -> pd.Series:
    """
    SMA (Simple Moving Average) 계산
    
    Args:
        close: 종가 시리즈
        period: SMA 기간
    
    Returns:
        SMA 값 시리즈
    """
    return close.rolling(window=period).mean()


def calculate_macd(close: pd.Series, 
                   fast: int = 12, 
                   slow: int = 26, 
                   signal: int = 9) -> Dict[str, pd.Series]:
    """
    MACD (Moving Average Convergence Divergence) 계산
    
    Args:
        close: 종가 시리즈
        fast: 빠른 EMA 기간 (기본: 12)
        slow: 느린 EMA 기간 (기본: 26)
        signal: 시그널 EMA 기간 (기본: 9)
    
    Returns:
        {'macd': Series, 'signal': Series, 'histogram': Series}
    """
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }


# calculate_atr() 삭제 → utils.indicators 사용 (SSOT)


def calculate_bollinger_bands(close: pd.Series, 
                               period: int = 20, 
                               std_dev: float = 2.0) -> Dict[str, pd.Series]:
    """
    볼린저 밴드 계산
    
    Args:
        close: 종가 시리즈
        period: 기간 (기본: 20)
        std_dev: 표준편차 배수 (기본: 2.0)
    
    Returns:
        {'upper': Series, 'middle': Series, 'lower': Series}
    """
    middle = close.rolling(window=period).mean()
    std = close.rolling(window=period).std()
    
    upper = middle + (std * std_dev)
    lower = middle - (std * std_dev)
    
    return {
        'upper': upper,
        'middle': middle,
        'lower': lower
    }


def calculate_stochastic(high: pd.Series,
                          low: pd.Series,
                          close: pd.Series,
                          k_period: int = 14,
                          d_period: int = 3) -> Dict[str, pd.Series]:
    """
    스토캐스틱 계산
    
    Args:
        high: 고가 시리즈
        low: 저가 시리즈
        close: 종가 시리즈
        k_period: %K 기간
        d_period: %D 기간
    
    Returns:
        {'k': Series, 'd': Series}
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(window=d_period).mean()
    
    return {'k': k, 'd': d}


def calculate_indicators(df: pd.DataFrame,
                         params: Optional[Dict[str, Any]] = None) -> IndicatorSet:
    """
    통합 지표 계산 함수

    Args:
        df: OHLCV 데이터프레임 (columns: open, high, low, close, volume)
        params: 지표 파라미터 딕셔너리

    Returns:
        IndicatorSet 객체 (최신 지표 값들)

    Example:
        df = pd.DataFrame({'close': [...], 'high': [...], 'low': [...]})
        indicators = calculate_indicators(df, {'rsi_period': 14, 'ema_period': 20})
    """
    from utils.indicators import calculate_rsi, calculate_atr

    params = params or {}

    close = df['close']
    high = df.get('high', close)
    low = df.get('low', close)

    # RSI (utils.indicators 사용 - SSOT)
    rsi_period = params.get('rsi_period', 14)
    rsi = calculate_rsi(close, period=rsi_period, return_series=True)

    # EMA
    ema_period = params.get('ema_period', 20)
    ema = calculate_ema(close, ema_period)

    # MACD
    macd_fast = params.get('macd_fast', 12)
    macd_slow = params.get('macd_slow', 26)
    macd_signal = params.get('macd_signal', 9)
    macd_result = calculate_macd(close, macd_fast, macd_slow, macd_signal)

    # ATR (utils.indicators 사용 - SSOT)
    atr_period = params.get('atr_period', 14)
    atr_df = df[['high', 'low', 'close']].copy()
    atr = calculate_atr(atr_df, period=atr_period, return_series=True)

    # 볼린저 밴드
    bb_period = params.get('bb_period', 20)
    bb_std = params.get('bb_std', 2.0)
    bb = calculate_bollinger_bands(close, bb_period, bb_std)

    # 최신 값 반환
    return IndicatorSet(
        rsi=float(rsi.iloc[-1]) if len(rsi) > 0 else None,
        macd=float(macd_result['macd'].iloc[-1]) if len(macd_result['macd']) > 0 else None,
        macd_signal=float(macd_result['signal'].iloc[-1]) if len(macd_result['signal']) > 0 else None,
        macd_hist=float(macd_result['histogram'].iloc[-1]) if len(macd_result['histogram']) > 0 else None,
        ema=float(ema.iloc[-1]) if len(ema) > 0 else None,
        atr=float(atr.iloc[-1]) if len(atr) > 0 else None,
        bb_upper=float(bb['upper'].iloc[-1]) if len(bb['upper']) > 0 else None,
        bb_middle=float(bb['middle'].iloc[-1]) if len(bb['middle']) > 0 else None,
        bb_lower=float(bb['lower'].iloc[-1]) if len(bb['lower']) > 0 else None,
    )


def prepare_data(df: pd.DataFrame,
                  params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    데이터프레임에 필수 지표 추가 (add_indicators_to_df 별칭)
    
    Args:
        df: OHLCV 데이터프레임
        params: 지표 파라미터
    
    Returns:
        지표가 추가된 데이터프레임
    """
    return add_indicators_to_df(df, params)


def add_indicators_to_df(df: pd.DataFrame,
                          params: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    데이터프레임에 지표 컬럼 추가

    Args:
        df: OHLCV 데이터프레임
        params: 지표 파라미터

    Returns:
        지표가 추가된 데이터프레임
    """
    from utils.indicators import calculate_rsi, calculate_atr

    params = params or {}
    result = df.copy()

    close = df['close']

    # RSI (utils.indicators 사용 - SSOT)
    result['rsi'] = calculate_rsi(close, period=params.get('rsi_period', 14), return_series=True)

    # EMA
    result['ema'] = calculate_ema(close, params.get('ema_period', 20))

    # MACD
    macd = calculate_macd(
        close,
        params.get('macd_fast', 12),
        params.get('macd_slow', 26),
        params.get('macd_signal', 9)
    )
    result['macd'] = macd['macd']
    result['macd_signal'] = macd['signal']
    result['macd_hist'] = macd['histogram']

    # ATR (utils.indicators 사용 - SSOT)
    atr_df = df[['high', 'low', 'close']].copy()
    result['atr'] = calculate_atr(atr_df, period=params.get('atr_period', 14), return_series=True)

    return result
