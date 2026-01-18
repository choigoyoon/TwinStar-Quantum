# GUI/backtest/__init__.py
"""Backtest module - 분리된 백테스트 위젯들

기존 backtest_widget.py와 호환성 유지
"""

# 기존 파일에서 가져옴 (중복 방지)
try:
    from GUI.backtest_widget import (
        BacktestWorker,
        SingleBacktestWidget,
        MultiBacktestWidget,
        BacktestWidget
    )
except ImportError:
    BacktestWorker = None
    SingleBacktestWidget = None
    MultiBacktestWidget = None
    BacktestWidget = None

__all__ = [
    'BacktestWorker',
    'SingleBacktestWidget',
    'MultiBacktestWidget',
    'BacktestWidget'
]
