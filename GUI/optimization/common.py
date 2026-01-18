# GUI/optimization/common.py
"""공통 import 및 설정"""

import sys
import os
import logging

# PyQt6 imports
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QDoubleSpinBox, QCheckBox, QGroupBox,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QSpinBox, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor



logger = logging.getLogger(__name__)

# Path setup
current_dir = os.path.dirname(os.path.abspath(__file__))
gui_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(gui_dir)

for path in [project_root, gui_dir, current_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Constants
try:
    from constants import TF_MAPPING, DEFAULT_PARAMS, EXCHANGE_INFO, TF_RESAMPLE_MAP
except ImportError:
    try:
        from GUI.constants import TF_MAPPING, DEFAULT_PARAMS, EXCHANGE_INFO, TF_RESAMPLE_MAP
    except ImportError:
        TF_MAPPING = {'1h': '15min', '4h': '1h', '1d': '4h', '1w': '1d'}
        DEFAULT_PARAMS = {'atr_mult': 1.5, 'rsi_period': 14, 'entry_validity_hours': 12.0}
        EXCHANGE_INFO = {}
        TF_RESAMPLE_MAP = {}

# Paths
try:
    from paths import Paths # type: ignore
except ImportError:
    class Paths:
        BASE = os.getcwd()
        CONFIG = os.path.join(BASE, 'config')
        PRESETS = os.path.join(CONFIG, 'presets')
        CACHE = os.path.join(BASE, 'data/cache')

# Localization
try:
    from locales import t
except ImportError:
    def t(key, default=None):
        return default if default else key.split('.')[-1]

# Core imports
try:
    from core.optimization_logic import OptimizationEngine
except ImportError:
    OptimizationEngine = None

try:
    from core.strategy_core import AlphaX7Core
except ImportError:
    AlphaX7Core = None
