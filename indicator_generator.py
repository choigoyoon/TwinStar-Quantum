
import pandas as pd
import numpy as np

class IndicatorGenerator:
    """지표 생성기 Utility"""
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """모든 필수 지표 추가"""
        if df is None or df.empty:
            return df
            
        df = df.copy()
        
        # 기본 컬럼 확인
        if 'close' not in df.columns:
            return df
            
        # 1. RSI (14, 21)
        # Note: Using Wilders smoothing via ewm could be better, but sticking to simple/wilder approximation
        # Standard RSI usually uses Wilder's Smoothing (alpha=1/n)
        df['rsi_14'] = IndicatorGenerator.calculate_rsi(df['close'], 14)
        df['rsi_21'] = IndicatorGenerator.calculate_rsi(df['close'], 21)
        
        # 기본 rsi는 14로 설정 (필요 시 수정)
        df['rsi'] = df['rsi_14']
        
        # 2. ATR (14)
        if all(c in df.columns for c in ['high', 'low', 'close']):
            df['atr_14'] = IndicatorGenerator.calculate_atr(df, 14)
            df['atr'] = df['atr_14']
            
        # 3. MACD
        ema12 = df['close'].ewm(span=12, adjust=False).mean()
        ema26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = ema12 - ema26
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        return df
    
    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """RSI 계산 (Wilder's Smoothing 방식)"""
        delta = series.diff()
        
        # Gain/Loss 분리
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 첫 번째 평균 (Simple Average)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # 이후 (Wilder's Smoothing)
        # pandas ewm(com=period-1, adjust=False) approximates Wilder's
        # BUT for consistency with valid implementation:
        # avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
        # avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
        
        # Using EWM for better accuracy than simple rolling
        avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
        
    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """ATR 계산 (Simple Moving Average or Wilder's?)"""
        # unified_bot/strategy_core logic seemed to use rolling mean
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        
        # Using rolling mean (Simple) as usually done in simple bots
        # If needed, can switch to ewm(alpha=1/period)
        return true_range.rolling(window=period).mean()
