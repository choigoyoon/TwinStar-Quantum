
import pandas as pd
import numpy as np

class IndicatorGenerator:
    """기술적 지표 계산 클래스"""
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """모든 주요 지표 추가"""
        df = df.copy()
        
        # 1. 이동평균 (MA)
        df = IndicatorGenerator.add_moving_averages(df)
        
        # 2. RSI
        df = IndicatorGenerator.add_rsi(df)
        
        # 3. MACD
        df = IndicatorGenerator.add_macd(df)
        
        # 4. ATR (변동성)
        df = IndicatorGenerator.add_atr(df)
        
        # 5. 볼린저 밴드
        df = IndicatorGenerator.add_bollinger_bands(df)
        
        # 6. 피벗 포인트 (일일 기준, 여기서는 캔들 기준 단순 계산)
        df = IndicatorGenerator.add_pivot_points(df)
        
        return df

    @staticmethod
    def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
        """SMA/EMA 추가"""
        close = df['close']
        
        # SMA
        for period in [5, 10, 20, 50, 120, 200]:
            df[f'sma_{period}'] = close.rolling(window=period).mean()
            
        # EMA
        for period in [9, 12, 26]:
            df[f'ema_{period}'] = close.ewm(span=period, adjust=False).mean()
            
        return df

    @staticmethod
    def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """RSI 추가"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        df[f'rsi_{period}'] = 100 - (100 / (1 + rs))
        
        # EMA 버전 (더 정확함)
        gain_ema = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        loss_ema = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
        rs_ema = gain_ema / loss_ema
        df[f'rsi_{period}_ema'] = 100 - (100 / (1 + rs_ema))
        
        return df

    @staticmethod
    def add_macd(df: pd.DataFrame, fast=12, slow=26, signal=9) -> pd.DataFrame:
        """MACD 추가"""
        exp1 = df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow, adjust=False).mean()
        
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        return df

    @staticmethod
    def add_atr(df: pd.DataFrame, period=14) -> pd.DataFrame:
        """ATR 추가"""
        high = df['high']
        low = df['low']
        close = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = abs(high - close)
        tr3 = abs(low - close)
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df[f'atr_{period}'] = tr.rolling(window=period).mean() # SMA 방식
        # df[f'atr_{period}'] = tr.ewm(alpha=1/period, adjust=False).mean() # EMA 방식
        
        return df

    @staticmethod
    def add_bollinger_bands(df: pd.DataFrame, period=20, num_std=2) -> pd.DataFrame:
        """볼린저 밴드 추가"""
        sma = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        
        df['bb_upper'] = sma + (std * num_std)
        df['bb_lower'] = sma - (std * num_std)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / sma
        
        return df
    
    @staticmethod
    def add_pivot_points(df: pd.DataFrame) -> pd.DataFrame:
        """
        캔들 기준 피벗 (Next candle preview)
        Typical Price = (High + Low + Close) / 3
        """
        high = df['high']
        low = df['low']
        close = df['close']
        
        pp = (high + low + close) / 3
        
        df['pivot'] = pp
        df['r1'] = (2 * pp) - low
        df['s1'] = (2 * pp) - high
        df['r2'] = pp + (high - low)
        df['s2'] = pp - (high - low)
        
        return df
