"""
백테스트 모듈
============

백테스트 실행 및 메트릭 계산

Usage:
    from trading.backtest import (
        BacktestEngine,
        Optimizer,
        calculate_mdd,
        calculate_backtest_metrics,
    )
"""

# 메트릭 계산 함수
from .metrics import (
    calculate_mdd,
    calculate_backtest_metrics,
    calculate_sharpe_ratio,
    calculate_profit_factor,
    calculate_win_rate,
)

# 기존 엔진/최적화 모듈
from .engine import BacktestEngine
from .optimizer import Optimizer

__all__ = [
    # 엔진
    'BacktestEngine',
    'Optimizer',
    # 메트릭
    'calculate_mdd',
    'calculate_backtest_metrics',
    'calculate_sharpe_ratio',
    'calculate_profit_factor',
    'calculate_win_rate',
]
