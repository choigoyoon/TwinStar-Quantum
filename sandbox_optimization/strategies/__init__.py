"""
전략 모듈
=========

두 가지 패턴 탐지 전략:
    - MACDStrategy: MACD 히스토그램 기반 W/M 패턴
    - ADXDIStrategy: +DI/-DI 크로스오버 기반 W/M 패턴
"""

from .macd import MACDStrategy
from .adxdi import ADXDIStrategy

__all__ = ['MACDStrategy', 'ADXDIStrategy']


def get_strategy(name: str):
    """전략 이름으로 클래스 반환"""
    strategies = {
        'macd': MACDStrategy,
        'adxdi': ADXDIStrategy,
    }
    return strategies.get(name.lower())


def list_strategies():
    """사용 가능한 전략 목록"""
    return {
        'macd': {
            'name': 'MACD Strategy',
            'description': 'MACD 히스토그램 부호 전환 기반 W/M 패턴 탐지',
            'class': MACDStrategy,
        },
        'adxdi': {
            'name': 'ADX/DI Strategy', 
            'description': '+DI/-DI 골든/데드 크로스 기반 W/M 패턴 탐지',
            'class': ADXDIStrategy,
        },
    }
