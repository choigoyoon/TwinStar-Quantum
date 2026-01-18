"""
TwinStar Quantum - Optimization Widgets
=======================================

최적화 관련 UI 컴포넌트들

구조:
    optimization/
    ├── __init__.py          ← 이 파일 (공개 API)
    ├── main.py              ← 메인 최적화 탭 컨테이너
    ├── single.py            ← 싱글 심볼 최적화 위젯
    ├── batch.py             ← 배치 최적화 위젯
    ├── params.py            ← 파라미터 입력 위젯들
    ├── worker.py            ← 백그라운드 워커
    ├── heatmap.py           ← GPU 가속 히트맵 위젯 (PyQtGraph)
    └── results_viewer.py    ← 모드/등급별 결과 뷰어

사용법:
    from ui.widgets.optimization import OptimizationWidget, HeatmapViewer

    widget = OptimizationWidget()
    widget.settings_applied.connect(on_settings_applied)

    heatmap = HeatmapViewer()
    heatmap.update_heatmap(data, x_labels, y_labels)
"""

from .main import OptimizationWidget
from .params import ParamRangeWidget, ParamChoiceWidget
from .worker import OptimizationWorker
from .heatmap import (
    GPUHeatmapWidget,
    HeatmapControlPanel,
    HeatmapViewer,
    create_colormap_lut,
    COLORMAPS,
)
from .results_viewer import ModeGradeResultsViewer

__all__ = [
    'OptimizationWidget',
    'ParamRangeWidget',
    'ParamChoiceWidget',
    'OptimizationWorker',
    'GPUHeatmapWidget',
    'HeatmapControlPanel',
    'HeatmapViewer',
    'ModeGradeResultsViewer',
    'create_colormap_lut',
    'COLORMAPS',
]
