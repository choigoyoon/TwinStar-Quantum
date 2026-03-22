"""
Trading Strategies Module
=========================

전략 모듈: BaseStrategy, MACD, ADX/DI

모듈 구조:
    base.py   - BaseStrategy 추상 클래스
    macd.py   - MACD 히스토그램 W/M 패턴 전략
    adxdi.py  - ADX/DI 크로스오버 W/M 패턴 전략

사용법:
    from trading.strategies import MACDStrategy, ADXDIStrategy
    
    macd = MACDStrategy()
    result = macd.backtest(df, timeframe='1h')
"""

from .base import BaseStrategy
from .macd import MACDStrategy
from .adxdi import ADXDIStrategy


# 전략 레지스트리
STRATEGIES = {
    'macd': MACDStrategy,
    'adxdi': ADXDIStrategy,
}


def get_strategy(name: str, params=None):
    """
    전략 인스턴스 생성
    
    Args:
        name: 전략 이름 ('macd', 'adxdi')
        params: 파라미터 딕셔너리 (선택)
    
    Returns:
        전략 인스턴스
    """
    name_lower = name.lower()
    if name_lower not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    return STRATEGIES[name_lower](params)


def list_strategies():
    """사용 가능한 전략 목록 반환"""
    return list(STRATEGIES.keys())


__all__ = [
    'BaseStrategy',
    'MACDStrategy',
    'ADXDIStrategy',
    'STRATEGIES',
    'get_strategy',
    'list_strategies',
]
