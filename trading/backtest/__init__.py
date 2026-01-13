"""
Trading Backtest Module
=======================

백테스트 엔진 및 최적화

모듈 구조:
    engine.py    - BacktestEngine (백테스트 실행)
    optimizer.py - Optimizer (파라미터 그리드 서치)

사용법:
    from trading.backtest import BacktestEngine, Optimizer
    
    # 백테스트
    engine = BacktestEngine()
    result = engine.run(df, strategy, timeframe='1h')
    
    # 최적화
    optimizer = Optimizer()
    results = optimizer.grid_search(df, strategy, timeframe='1h')
"""

from .engine import BacktestEngine
from .optimizer import Optimizer


__all__ = [
    'BacktestEngine',
    'Optimizer',
]
