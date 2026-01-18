"""
백테스트 모듈
============

백테스트 실행 엔진 및 최적화

Usage:
    from trading.backtest import BacktestEngine, Optimizer

    # 메트릭 계산은 utils.metrics 사용
    from utils.metrics import (
        calculate_mdd,
        calculate_backtest_metrics,
        calculate_sharpe_ratio,
        calculate_profit_factor,
        calculate_win_rate,
    )
"""

# 백테스트 엔진 및 최적화
from .engine import BacktestEngine
from .optimizer import Optimizer

# 하위 호환성을 위한 메트릭 함수 재export (DEPRECATED)
# 새 코드는 utils.metrics 직접 사용 권장
from utils.metrics import (
    calculate_mdd,
    calculate_backtest_metrics,
    calculate_sharpe_ratio,
    calculate_profit_factor,
    calculate_win_rate,
)

__all__ = [
    # 엔진
    'BacktestEngine',
    'Optimizer',
    # 메트릭 (DEPRECATED - utils.metrics 사용 권장)
    'calculate_mdd',
    'calculate_backtest_metrics',
    'calculate_sharpe_ratio',
    'calculate_profit_factor',
    'calculate_win_rate',
]
