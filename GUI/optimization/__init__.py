# GUI/optimization/__init__.py
"""Optimization module - 분리된 최적화 위젯들

기존 optimization_widget.py와 호환성 유지:
- 새 코드: from GUI.optimization import OptimizationWidget
- 기존 코드: from GUI.optimization_widget import OptimizationWidget (여전히 동작)
"""

from .worker import OptimizationWorker
from .params import ParamRangeWidget, ParamChoiceWidget

# 메인 위젯들은 기존 파일에서 가져옴 (중복 방지)
try:
    from GUI.optimization_widget import (
        SingleOptimizerWidget,
        BatchOptimizerWidget, 
        OptimizationWidget
    )
except ImportError:
    from .main import OptimizationWidget
    SingleOptimizerWidget = None
    BatchOptimizerWidget = None

__all__ = [
    'OptimizationWorker',
    'ParamRangeWidget', 
    'ParamChoiceWidget',
    'SingleOptimizerWidget',
    'BatchOptimizerWidget',
    'OptimizationWidget'
]
