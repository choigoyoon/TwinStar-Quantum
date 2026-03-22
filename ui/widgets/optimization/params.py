"""
TwinStar Quantum - Parameter Input Widgets
==========================================

최적화 파라미터 입력 컴포넌트들

토큰 기반 디자인 시스템 적용 (v7.12 - 2026-01-16)
"""

import numpy as np
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel,
    QDoubleSpinBox, QCheckBox, QSpinBox
)

# 디자인 시스템 import (SSOT)
from ui.design_system.tokens import Colors, Typography, Spacing, Radius, Size


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
    
    def _init_ui(self, min_val: float, max_val: float, step: float, decimals: int):
        if self.tooltip:
            self.setToolTip(self.tooltip)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.i_space_2)  # 8px

        # 라벨
        label = QLabel(f"{self.name}:")
        label.setMinimumWidth(Size.label_min_width)  # Issue #3: Size 토큰 사용 (v7.27)
        label.setStyleSheet(f"""
            color: {Colors.text_secondary};
            font-size: {Typography.text_sm};
        """)
        layout.addWidget(label)

        # SpinBox 공통 스타일
        spinbox_style = f"""
            QDoubleSpinBox {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_1} {Spacing.space_2};
                font-size: {Typography.text_sm};
                min-width: 80px;
            }}
            QDoubleSpinBox:hover {{
                border-color: {Colors.accent_primary};
            }}
            QDoubleSpinBox:focus {{
                border-color: {Colors.accent_primary};
                background-color: {Colors.bg_surface};
            }}
        """

        # 최소값
        min_label = QLabel("최소")
        min_label.setStyleSheet(f"font-size: {Typography.text_xs}; color: {Colors.text_secondary};")
        layout.addWidget(min_label)

        self.min_spin = QDoubleSpinBox()
        self.min_spin.setRange(0, 100)
        self.min_spin.setDecimals(decimals)
        self.min_spin.setValue(min_val)
        self.min_spin.setStyleSheet(spinbox_style)
        layout.addWidget(self.min_spin)

        # 최대값
        max_label = QLabel("최대")
        max_label.setStyleSheet(f"font-size: {Typography.text_xs}; color: {Colors.text_secondary};")
        layout.addWidget(max_label)

        self.max_spin = QDoubleSpinBox()
        self.max_spin.setRange(0, 100)
        self.max_spin.setDecimals(decimals)
        self.max_spin.setValue(max_val)
        self.max_spin.setStyleSheet(spinbox_style)
        layout.addWidget(self.max_spin)

        # 스텝
        step_label = QLabel("단계")
        step_label.setStyleSheet(f"font-size: {Typography.text_xs}; color: {Colors.text_secondary};")
        layout.addWidget(step_label)

        self.step_spin = QDoubleSpinBox()
        self.step_spin.setRange(0.01, 10)
        self.step_spin.setDecimals(decimals)
        self.step_spin.setValue(step)
        self.step_spin.setStyleSheet(spinbox_style)
        layout.addWidget(self.step_spin)

        # HIGH #6: 입력 검증 추가 (v7.27)
        # min <= max 보장
        self.min_spin.valueChanged.connect(self._validate_min_max)
        self.max_spin.valueChanged.connect(self._validate_min_max)

        layout.addStretch()

    def _validate_min_max(self):
        """HIGH #6: min <= max 검증 (v7.27)

        최소값이 최대값보다 크면 자동으로 최대값을 최소값으로 조정합니다.
        """
        min_val = self.min_spin.value()
        max_val = self.max_spin.value()

        if min_val > max_val:
            # 최대값을 최소값으로 자동 조정
            self.max_spin.setValue(min_val)

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
        checked_indices: list | None = None,
        tooltip: str = "",
        parent=None
    ):
        super().__init__(parent)
        self.name = name
        self.choices = choices
        self.tooltip = tooltip
        self._init_ui(checked_indices or [0])
    
    def _init_ui(self, checked_indices: list):
        if self.tooltip:
            self.setToolTip(self.tooltip)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.i_space_2)  # 8px

        # 라벨
        label = QLabel(f"{self.name}:")
        label.setMinimumWidth(Size.label_min_width)  # Issue #3: Size 토큰 사용 (v7.27)
        label.setStyleSheet(f"""
            color: {Colors.text_secondary};
            font-size: {Typography.text_sm};
        """)
        layout.addWidget(label)

        # 체크박스들
        self.checkboxes: list[QCheckBox] = []
        for i, choice in enumerate(self.choices):
            cb = QCheckBox(str(choice))
            cb.setChecked(i in checked_indices)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {Colors.text_primary};
                    font-size: {Typography.text_sm};
                    spacing: {Spacing.space_1};
                }}
                QCheckBox::indicator {{
                    width: 16px;
                    height: 16px;
                    border: 1px solid {Colors.border_muted};
                    border-radius: {Radius.radius_sm};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {Colors.accent_primary};
                    border-color: {Colors.accent_primary};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {Colors.accent_primary};
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
    
    def _init_ui(self, min_val: int, max_val: int, step: int):
        if self.tooltip:
            self.setToolTip(self.tooltip)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(Spacing.i_space_2)  # 8px

        # 라벨
        label = QLabel(f"{self.name}:")
        label.setMinimumWidth(Size.label_min_width)  # Issue #3: Size 토큰 사용 (v7.27)
        label.setStyleSheet(f"""
            color: {Colors.text_secondary};
            font-size: {Typography.text_sm};
        """)
        layout.addWidget(label)

        # SpinBox 공통 스타일
        spinbox_style = f"""
            QSpinBox {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_1} {Spacing.space_2};
                font-size: {Typography.text_sm};
                min-width: 80px;
            }}
            QSpinBox:hover {{
                border-color: {Colors.accent_primary};
            }}
            QSpinBox:focus {{
                border-color: {Colors.accent_primary};
                background-color: {Colors.bg_surface};
            }}
        """

        # 최소값
        min_label = QLabel("최소")
        min_label.setStyleSheet(f"font-size: {Typography.text_xs}; color: {Colors.text_secondary};")
        layout.addWidget(min_label)

        self.min_spin = QSpinBox()
        self.min_spin.setRange(1, 1000)
        self.min_spin.setValue(min_val)
        self.min_spin.setStyleSheet(spinbox_style)
        layout.addWidget(self.min_spin)

        # 최대값
        max_label = QLabel("최대")
        max_label.setStyleSheet(f"font-size: {Typography.text_xs}; color: {Colors.text_secondary};")
        layout.addWidget(max_label)

        self.max_spin = QSpinBox()
        self.max_spin.setRange(1, 1000)
        self.max_spin.setValue(max_val)
        self.max_spin.setStyleSheet(spinbox_style)
        layout.addWidget(self.max_spin)

        # 스텝
        step_label = QLabel("단계")
        step_label.setStyleSheet(f"font-size: {Typography.text_xs}; color: {Colors.text_secondary};")
        layout.addWidget(step_label)

        self.step_spin = QSpinBox()
        self.step_spin.setRange(1, 100)
        self.step_spin.setValue(step)
        self.step_spin.setStyleSheet(spinbox_style)
        layout.addWidget(self.step_spin)

        # HIGH #6: 입력 검증 추가 (v7.27)
        # min <= max 보장
        self.min_spin.valueChanged.connect(self._validate_min_max)
        self.max_spin.valueChanged.connect(self._validate_min_max)

        layout.addStretch()

    def _validate_min_max(self):
        """HIGH #6: min <= max 검증 (v7.27)

        최소값이 최대값보다 크면 자동으로 최대값을 최소값으로 조정합니다.
        """
        min_val = self.min_spin.value()
        max_val = self.max_spin.value()

        if min_val > max_val:
            # 최대값을 최소값으로 자동 조정
            self.max_spin.setValue(min_val)

    def get_values(self) -> list:
        """범위에서 정수 값 리스트 생성"""
        min_v = self.min_spin.value()
        max_v = self.max_spin.value()
        step_v = self.step_spin.value()

        if step_v <= 0:
            return [min_v]

        return list(range(min_v, max_v + 1, step_v))

    def set_values(self, min_val: int, max_val: int, step: int):
        """값 설정"""
        self.min_spin.setValue(min_val)
        self.max_spin.setValue(max_val)
        self.step_spin.setValue(step)
