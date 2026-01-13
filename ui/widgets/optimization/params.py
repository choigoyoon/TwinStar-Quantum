"""
TwinStar Quantum - Parameter Input Widgets
==========================================

최적화 파라미터 입력 컴포넌트들
"""

import numpy as np
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, 
    QDoubleSpinBox, QCheckBox
)

# 디자인 시스템 import
try:
    from ui.design_system import Colors, Typography
except ImportError:
    # 폴백
    class Colors:
        text_secondary = "#8b949e"
        bg_elevated = "#21262d"
        text_primary = "#f0f6fc"
    class Typography:
        pass


class ParamRangeWidget(QWidget):
    """
    파라미터 범위 입력 위젯
    
    min/max/step을 설정하여 그리드 서치용 값 리스트 생성
    
    사용법:
        widget = ParamRangeWidget("ATR 배수", 1.0, 3.0, 0.5)
        values = widget.get_values()  # [1.0, 1.5, 2.0, 2.5, 3.0]
    """
    
    def __init__(
        self, 
        name: str, 
        min_val: float, 
        max_val: float, 
        step: float, 
        decimals: int = 2, 
        tooltip: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.name = name
        self.tooltip = tooltip
        self._init_ui(min_val, max_val, step, decimals)
    
    def _init_ui(self, min_val, max_val, step, decimals):
        if self.tooltip:
            self.setToolTip(self.tooltip)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 라벨
        label = QLabel(f"{self.name}:")
        label.setMinimumWidth(100)
        label.setStyleSheet(f"color: {Colors.text_secondary};")
        layout.addWidget(label)
        
        # 최소값
        layout.addWidget(QLabel("최소"))
        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(0, 100)
        self.min_spin.setDecimals(decimals)
        self.min_spin.setValue(min_val)
        self.min_spin.setStyleSheet(f"""
            background: {Colors.bg_elevated}; 
            color: {Colors.text_primary};
            border: 1px solid #30363d;
            border-radius: 4px;
            padding: 4px;
        """)
        layout.addWidget(self.min_spin)
        
        # 최대값
        layout.addWidget(QLabel("최대"))
        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(0, 100)
        self.max_spin.setDecimals(decimals)
        self.max_spin.setValue(max_val)
        self.max_spin.setStyleSheet(self.min_spin.styleSheet())
        layout.addWidget(self.max_spin)
        
        # 스텝
        layout.addWidget(QLabel("단계"))
        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.01, 10)
        self.step_spin.setDecimals(decimals)
        self.step_spin.setValue(step)
        self.step_spin.setStyleSheet(self.min_spin.styleSheet())
        layout.addWidget(self.step_spin)
        
        layout.addStretch()
    
    def get_values(self) -> list:
        """범위에서 값 리스트 생성"""
        min_v = self.min_spin.value()
        max_v = self.max_spin.value()
        step_v = self.step_spin.value()
        
        if step_v <= 0:
            return [min_v]
        
        values = list(np.arange(min_v, max_v + step_v / 2, step_v))
        return [round(v, 2) for v in values]
    
    def set_values(self, min_val: float, max_val: float, step: float):
        """값 설정"""
        self.min_spin.setValue(min_val)
        self.max_spin.setValue(max_val)
        self.step_spin.setValue(step)


class ParamChoiceWidget(QWidget):
    """
    선택형 파라미터 위젯
    
    여러 옵션 중 선택 가능
    
    사용법:
        widget = ParamChoiceWidget("타임프레임", ["1h", "4h", "1d"])
        selected = widget.get_values()  # 체크된 항목들
    """
    
    def __init__(
        self, 
        name: str, 
        choices: list, 
        checked_indices: list = None, 
        tooltip: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.name = name
        self.choices = choices
        self.tooltip = tooltip
        self._init_ui(checked_indices or [0])
    
    def _init_ui(self, checked_indices):
        if self.tooltip:
            self.setToolTip(self.tooltip)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 라벨
        label = QLabel(f"{self.name}:")
        label.setMinimumWidth(100)
        label.setStyleSheet(f"color: {Colors.text_secondary};")
        layout.addWidget(label)
        
        # 체크박스들
        self.checkboxes = []
        for i, choice in enumerate(self.choices):
            cb = QCheckBox(str(choice))
            cb.setChecked(i in checked_indices)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {Colors.text_primary};
                    spacing: 4px;
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                }}
            """)
            self.checkboxes.append(cb)
            layout.addWidget(cb)
        
        layout.addStretch()
    
    def get_values(self) -> list:
        """선택된 값들 반환"""
        return [
            self.choices[i] 
            for i, cb in enumerate(self.checkboxes) 
            if cb.isChecked()
        ]
    
    def set_checked(self, indices: list):
        """특정 인덱스들 체크"""
        for i, cb in enumerate(self.checkboxes):
            cb.setChecked(i in indices)


class ParamIntRangeWidget(QWidget):
    """
    정수 범위 파라미터 위젯
    
    사용법:
        widget = ParamIntRangeWidget("RSI 기간", 7, 21, 2)
        values = widget.get_values()  # [7, 9, 11, 13, 15, 17, 19, 21]
    """
    
    def __init__(
        self, 
        name: str, 
        min_val: int, 
        max_val: int, 
        step: int = 1,
        tooltip: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.name = name
        self.tooltip = tooltip
        self._init_ui(min_val, max_val, step)
    
    def _init_ui(self, min_val, max_val, step):
        from PyQt5.QtWidgets import QSpinBox
        
        if self.tooltip:
            self.setToolTip(self.tooltip)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 라벨
        label = QLabel(f"{self.name}:")
        label.setMinimumWidth(100)
        label.setStyleSheet(f"color: {Colors.text_secondary};")
        layout.addWidget(label)
        
        style = f"""
            background: {Colors.bg_elevated}; 
            color: {Colors.text_primary};
            border: 1px solid #30363d;
            border-radius: 4px;
            padding: 4px;
        """
        
        # 최소값
        layout.addWidget(QLabel("최소"))
        self.min_spin = QSpinBox()
        self.min_spin.setRange(1, 1000)
        self.min_spin.setValue(min_val)
        self.min_spin.setStyleSheet(style)
        layout.addWidget(self.min_spin)
        
        # 최대값
        layout.addWidget(QLabel("최대"))
        self.max_spin = QSpinBox()
        self.max_spin.setRange(1, 1000)
        self.max_spin.setValue(max_val)
        self.max_spin.setStyleSheet(style)
        layout.addWidget(self.max_spin)
        
        # 스텝
        layout.addWidget(QLabel("단계"))
        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 100)
        self.step_spin.setValue(step)
        self.step_spin.setStyleSheet(style)
        layout.addWidget(self.step_spin)
        
        layout.addStretch()
    
    def get_values(self) -> list:
        """범위에서 정수 값 리스트 생성"""
        min_v = self.min_spin.value()
        max_v = self.max_spin.value()
        step_v = self.step_spin.value()
        
        if step_v <= 0:
            return [min_v]
        
        return list(range(min_v, max_v + 1, step_v))
