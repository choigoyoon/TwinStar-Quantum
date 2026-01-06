"""
indicator_generator.py
지표 생성기 - utils.indicators 모듈 래퍼

Note: 이 파일은 하위 호환성을 위해 유지됩니다.
      새 코드에서는 utils.indicators를 직접 import하세요.
"""

from utils.indicators import (
    calculate_rsi,
    calculate_atr,
    calculate_macd,
    calculate_ema,
    add_all_indicators
)


class IndicatorGenerator:
    """
    지표 생성기 Utility
    
    Note: 레거시 호환용 클래스. 새 코드에서는 utils.indicators 모듈 함수를 직접 사용하세요.
    """
    
    @staticmethod
    def add_all_indicators(df):
        """모든 필수 지표 추가"""
        return add_all_indicators(df)
    
    @staticmethod
    def calculate_rsi(series, period=14):
        """RSI 계산 (SMA 방식)"""
        return calculate_rsi(series, period=period, return_series=True)
    
    @staticmethod
    def calculate_atr(df, period=14):
        """ATR 계산"""
        return calculate_atr(df, period=period, return_series=True)

