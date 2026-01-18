# GUI/optimization/batch_optimizer.py
"""배치 최적화 위젯 - 기존 optimization_widget.py에서 import"""

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
gui_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(gui_dir)

for path in [project_root, gui_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# 직접 접근용 (하위 호환성)
try:
    from GUI.optimization_widget import BatchOptimizerWidget
except ImportError:
    BatchOptimizerWidget = None
