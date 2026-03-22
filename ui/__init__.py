"""
UI Package for Trading System
=============================

trading/ 패키지 기반의 새로운 UI 시스템

구조:
    ui/
    ├── __init__.py          ← 이 파일
    ├── design_system/       ← 디자인 시스템 (PyQt5 독립)
    │   ├── tokens.py        ← 디자인 토큰
    │   └── theme.py         ← 테마 생성기
    ├── widgets/             ← UI 위젯
    │   ├── backtest.py      ← 백테스트 위젯
    │   ├── optimization.py  ← 최적화 위젯
    │   └── results.py       ← 결과 표시 위젯
    ├── workers/             ← 백그라운드 작업
    │   └── tasks.py         ← QThread 작업들
    └── styles.py            ← 스타일 정의

사용법:
    # 디자인 시스템 (PyQt5 불필요)
    from ui.design_system import Colors, Typography, Spacing, Radius
    from ui.design_system import ThemeGenerator
    
    # UI 위젯 (PyQt5 필요)
    from ui import BacktestWidget, OptimizationWidget
    from ui.workers import BacktestWorker, OptimizationWorker
"""

__version__ = "1.0.0"

# Design System은 항상 사용 가능 (PyQt5 의존성 없음)
from .design_system import (
    Colors,
    Typography,
    Spacing,
    Radius,
    Shadow,
    get_gradient,
    ThemeGenerator,
)

# UI 위젯은 PyQt5가 있을 때만 import
try:
    from .widgets.backtest import BacktestWidget
    from .widgets.optimization import OptimizationWidget
    from .widgets.results import ResultsWidget, GradeLabel
    from .workers.tasks import BacktestWorker, OptimizationWorker
    
    _PYQT_AVAILABLE = True
except ImportError:
    # PyQt5가 없는 환경 (테스트, CLI 등)
    BacktestWidget = None
    OptimizationWidget = None
    ResultsWidget = None
    GradeLabel = None
    BacktestWorker = None
    OptimizationWorker = None
    
    _PYQT_AVAILABLE = False

__all__ = [
    '__version__',
    # Design System (항상 사용 가능)
    'Colors',
    'Typography',
    'Spacing',
    'Radius',
    'Shadow',
    'get_gradient',
    'ThemeGenerator',
    # Widgets (PyQt5 필요)
    'BacktestWidget',
    'OptimizationWidget',
    'ResultsWidget',
    'GradeLabel',
    # Workers (PyQt5 필요)
    'BacktestWorker',
    'OptimizationWorker',
    # Utils
    '_PYQT_AVAILABLE',
]
