# GUI/optimization/params.py
"""파라미터 위젯 - 범위/선택 입력"""

import numpy as np
from .common import *


class ParamRangeWidget(QWidget):
    """Parameter range input widget"""
    
    def __init__(self, name: str, min_val: float, max_val: float, 
                 step: float, decimals: int = 2, tooltip: str = "", parent=None):
        super().__init__(parent)
        self.name = name
        self.tooltip = tooltip
        self._init_ui(min_val, max_val, step, decimals)
    
    def _init_ui(self, min_val, max_val, step, decimals):
        if self.tooltip:
            self.setToolTip(self.tooltip)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(f"{self.name}:")
        label.setMinimumWidth(80)
        label.setStyleSheet("color: #888;")
        layout.addWidget(label)
        
        layout.addWidget(QLabel("최소"))
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(0, 100)
        self.min_spin.setDecimals(decimals)
        self.min_spin.setValue(min_val)
        self.min_spin.setStyleSheet("background: #2b2b2b; color: white;")
        layout.addWidget(self.min_spin)
        
        layout.addWidget(QLabel("최대"))
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(0, 100)
        self.max_spin.setDecimals(decimals)
        self.max_spin.setValue(max_val)
        self.max_spin.setStyleSheet("background: #2b2b2b; color: white;")
        layout.addWidget(self.max_spin)
        
        layout.addWidget(QLabel("단계"))
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.01, 10)
        self.step_spin.setDecimals(decimals)
        self.step_spin.setValue(step)
        self.step_spin.setStyleSheet("background: #2b2b2b; color: white;")
        layout.addWidget(self.step_spin)
        
        layout.addStretch()
    
    def get_values(self) -> list:
        """Generate value list from range"""
        min_v = self.min_spin.value()
        max_v = self.max_spin.value()
        step_v = self.step_spin.value()
        
        if step_v <= 0:
            return [min_v]
        
        values = list(np.arange(min_v, max_v + step_v/2, step_v))
        return [round(v, 2) for v in values]


class ParamChoiceWidget(QWidget):
    """Choice parameter widget (list)"""
    
    def __init__(self, name: str, choices: list, checked_indices: list = None, 
                 tooltip: str = "", parent=None):
        super().__init__(parent)
        self.name = name
        self.choices = choices
        self.checkboxes = []
        self._init_ui(checked_indices or [0])
    
    def _init_ui(self, checked_indices):
        if hasattr(self, 'tooltip') and self.tooltip:
            self.setToolTip(self.tooltip)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QLabel(f"{self.name}:")
        label.setMinimumWidth(80)
        label.setStyleSheet("color: #888;")
        layout.addWidget(label)
        
        for i, choice in enumerate(self.choices):
            cb = QCheckBox(str(choice))
            cb.setChecked(i in checked_indices)
            cb.setStyleSheet("color: white;")
            self.checkboxes.append(cb)
            layout.addWidget(cb)
        
        layout.addStretch()
    
    def get_values(self) -> list:
        """Get checked values"""
        return [self.choices[i] for i, cb in enumerate(self.checkboxes) if cb.isChecked()]
