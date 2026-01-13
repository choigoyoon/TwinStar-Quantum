"""
지표 계산
=========

ATR, EMA, MACD, ADX, Stochastic 등 기술적 지표 계산
백테스트 + 실거래 모두 동일한 계산식 사용
"""

import numpy as np
import pandas as pd
from typing import Dict


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    모든 기술적 지표 계산
    
    계산 지표:
        - ATR (14): 손절 거리 계산용
        - EMA (21, 50): 추세 판단용
        - MACD (12, 26, 9): MACD 전략용
        - ADX (14) + DI: ADX/DI 전략용
        - Stochastic K (14): 필터용
        - Volume Ratio: 필터용 (선택적)
    
    Args:
        df: OHLCV 데이터프레임 (open, high, low, close, volume)
    
    Returns:
        지표가 추가된 데이터프레임
    """
    df = df.copy()
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    # =========================================================================
    # ATR (14) - 손절 거리 계산용
    # =========================================================================
    tr = np.maximum(
        high - low,
        np.maximum(
            np.abs(high - np.roll(close, 1)),
            np.abs(low - np.roll(close, 1))
        )
    )
    tr[0] = high[0] - low[0]
    df['atr'] = pd.Series(tr).rolling(14).mean().values
    
    # =========================================================================
    # EMA (21, 50) - 추세 판단용
    # =========================================================================
    df['ema_21'] = pd.Series(close).ewm(span=21, adjust=False).mean().values
    df['ema_50'] = pd.Series(close).ewm(span=50, adjust=False).mean().values
    
    # =========================================================================
    # MACD (12, 26, 9) - MACD 전략용
    # =========================================================================
    ema_12 = pd.Series(close).ewm(span=12, adjust=False).mean().values
    ema_26 = pd.Series(close).ewm(span=26, adjust=False).mean().values
    macd = ema_12 - ema_26
    macd_signal = pd.Series(macd).ewm(span=9, adjust=False).mean().values
    df['macd_hist'] = macd - macd_signal
    
    # =========================================================================
    # ADX (14) + DI - ADX/DI 전략용
    # =========================================================================
    plus_dm = np.diff(high, prepend=high[0])
    minus_dm = -np.diff(low, prepend=low[0])
    plus_dm = np.where((plus_dm > minus_dm) & (plus_dm > 0), plus_dm, 0)
    minus_dm = np.where((minus_dm > plus_dm) & (minus_dm > 0), minus_dm, 0)
    
    atr_smooth = pd.Series(tr).rolling(14).mean().values
    plus_di = 100 * pd.Series(plus_dm).rolling(14).mean().values / (atr_smooth + 1e-10)
    minus_di = 100 * pd.Series(minus_dm).rolling(14).mean().values / (atr_smooth + 1e-10)
    
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
    df['adx'] = pd.Series(dx).rolling(14).mean().values
    df['plus_di'] = plus_di
    df['minus_di'] = minus_di
    
    # =========================================================================
    # Stochastic K (14) - 필터용
    # =========================================================================
    low_14 = pd.Series(low).rolling(14).min().values
    high_14 = pd.Series(high).rolling(14).max().values
    df['stoch_k'] = 100 * (close - low_14) / (high_14 - low_14 + 1e-10)
    
    # =========================================================================
    # Volume Ratio - 필터용 (선택적)
    # =========================================================================
    if 'volume' in df.columns:
        vol = df['volume'].values
        vol_ma = pd.Series(vol).rolling(20).mean().values
        df['vol_ratio'] = vol / (vol_ma + 1e-10)
    else:
        df['vol_ratio'] = 1.0
    
    # =========================================================================
    # 추세 플래그 - 필터용
    # =========================================================================
    df['downtrend'] = df['ema_21'] < df['ema_50']
    df['uptrend'] = df['ema_21'] > df['ema_50']
    
    return df


def prepare_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    데이터 준비: 타임스탬프 정리 + 리샘플링 + 지표 계산
    
    Args:
        df: 원본 데이터프레임 (15분봉 등)
        timeframe: 목표 타임프레임 ('1h', '2h', '4h', etc.)
    
    Returns:
        리샘플링 + 지표 계산된 데이터프레임
    """
    df_work = df.copy()
    
    # 타임스탬프 정리
    if 'timestamp' not in df_work.columns:
        df_work = df_work.reset_index()
    
    df_work['timestamp'] = pd.to_datetime(df_work['timestamp'])
    df_work = df_work.sort_values('timestamp').reset_index(drop=True)
    df_work.set_index('timestamp', inplace=True)
    
    # 리샘플링
    df_tf = df_work.resample(timeframe).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()
    
    # 지표 계산
    df_tf = calculate_indicators(df_tf)
    
    return df_tf
