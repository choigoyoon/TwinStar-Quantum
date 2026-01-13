"""
UI Package for Trading System
=============================

trading/ 패키지 기반의 새로운 UI 시스템

구조:
    ui/
    ├── __init__.py          ← 이 파일
    ├── widgets/             ← UI 위젯
    │   ├── backtest.py      ← 백테스트 위젯
    │   ├── optimization.py  ← 최적화 위젯
    │   └── results.py       ← 결과 표시 위젯
    ├── workers/             ← 백그라운드 작업
    │   └── tasks.py         ← QThread 작업들
    └── styles.py            ← 스타일 정의

사용법:
    from ui import BacktestWidget, OptimizationWidget
    from ui.workers import BacktestWorker, OptimizationWorker
"""

__version__ = "1.0.0"

# Widgets
from .widgets.backtest import BacktestWidget
from .widgets.optimization import OptimizationWidget
from .widgets.results import ResultsWidget, GradeLabel

# Workers
from .workers.tasks import BacktestWorker, OptimizationWorker

__all__ = [
    '__version__',
    # Widgets
    'BacktestWidget',
    'OptimizationWidget',
    'ResultsWidget',
    'GradeLabel',
    # Workers
    'BacktestWorker',
    'OptimizationWorker',
]
