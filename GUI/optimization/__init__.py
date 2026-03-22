# GUI/optimization/__init__.py
"""Optimization module - 분리된 최적화 위젯들

신규 UI 시스템 (ui/widgets/optimization)으로 마이그레이션 완료
레거시 호환성 유지
"""

# 신규 UI 시스템에서 가져옴 (GUI.optimization_widget은 v7.16에서 삭제됨)
try:
    from ui.widgets.optimization import OptimizationWidget
    from ui.widgets.optimization.worker import OptimizationWorker
    from ui.widgets.optimization.params import ParamRangeWidget, ParamChoiceWidget
    from ui.widgets.optimization.single import SingleOptimizationWidget
    from ui.widgets.optimization.batch import BatchOptimizationWidget

    # 레거시 이름 호환성
    SingleOptimizerWidget = SingleOptimizationWidget
    BatchOptimizerWidget = BatchOptimizationWidget
except ImportError:
    # Fallback to local files if ui module not available
    from .worker import OptimizationWorker
    from .params import ParamRangeWidget, ParamChoiceWidget
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
