"""
백테스트 위젯 재사용 컴포넌트

StatLabel, ParameterFrame 등 공통 UI 컴포넌트 정의
"""

from PyQt6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt
from typing import Optional

from ui.design_system.tokens import ColorTokens

# 토큰 인스턴스
_tokens = ColorTokens()


class StatLabel(QFrame):
    """통계 표시 라벨 컴포넌트

    라벨과 값을 수직으로 배치한 통계 표시 위젯

    Example:
        stat_trades = StatLabel("Trades", "0")
        stat_trades.set_value("42")
        stat_trades.set_value("42", _tokens.success)
    """

    def __init__(
        self,
        label: str,
        value: str = "-",
        parent: Optional[QWidget] = None
    ):
        """
        Args:
            label: 상단 라벨 텍스트
            value: 초기 값 (기본값: "-")
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.value_label: QLabel  # 타입 명시
        self._init_ui(label, value)

    def _init_ui(self, label: str, value: str):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # 상단 라벨
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {_tokens.text_secondary}; font-size: 11px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        # 값 라벨
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            f"color: {_tokens.text_primary}; font-size: 14px; font-weight: bold;"
        )
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.value_label)

        # 프레임 스타일
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background: {_tokens.bg_surface};
                border: 1px solid {_tokens.border_default};
                border-radius: 4px;
            }}
        """)

    def set_value(self, value: str, color: Optional[str] = None):
        """값 업데이트

        Args:
            value: 표시할 값
            color: 텍스트 색상 (기본값: text_primary)
        """
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(
                f"color: {color}; font-size: 14px; font-weight: bold;"
            )
        else:
            self.value_label.setStyleSheet(
                f"color: {_tokens.text_primary}; font-size: 14px; font-weight: bold;"
            )


class ParameterFrame(QFrame):
    """파라미터 입력 프레임

    라벨과 입력 위젯을 수직으로 배치한 파라미터 입력 프레임

    Example:
        lev_spin = QSpinBox()
        lev_frame = ParameterFrame("Leverage", lev_spin)
    """

    def __init__(
        self,
        label: str,
        widget: QWidget,
        parent: Optional[QWidget] = None
    ):
        """
        Args:
            label: 상단 라벨 텍스트
            widget: 입력 위젯 (QSpinBox, QDoubleSpinBox, QComboBox 등)
            parent: 부모 위젯
        """
        super().__init__(parent)
        self.widget = widget
        self.value_label: Optional[QLabel] = None  # 선택적 값 표시 라벨
        self._init_ui(label)

    def _init_ui(self, label: str):
        """UI 초기화"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        # 상단 라벨
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color: {_tokens.text_secondary}; font-size: 11px;")
        layout.addWidget(lbl)

        # 입력 위젯
        layout.addWidget(self.widget)

        # 프레임 스타일
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(f"""
            QFrame {{
                background: {_tokens.bg_surface};
                border: 1px solid {_tokens.border_muted};
                border-radius: 4px;
            }}
        """)

    def add_value_label(self, initial_value: str = "-") -> QLabel:
        """값 표시 라벨 추가 (선택적)

        파라미터의 현재 값을 표시하는 라벨을 추가합니다.

        Args:
            initial_value: 초기 값

        Returns:
            생성된 QLabel 인스턴스
        """
        if self.value_label is not None:
            return self.value_label

        self.value_label = QLabel(initial_value)
        self.value_label.setStyleSheet(
            f"color: {_tokens.text_primary}; font-size: 12px; font-weight: bold;"
        )
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 레이아웃에 추가 (위젯 다음)
        layout = self.layout()
        if layout:
            layout.addWidget(self.value_label)

        return self.value_label

    def update_value_label(self, value: str):
        """값 표시 라벨 업데이트

        Args:
            value: 표시할 값
        """
        if self.value_label is not None:
            self.value_label.setText(value)


class ResultsTable(QFrame):
    """결과 테이블 컨테이너

    테이블 + 헤더를 포함한 결과 표시 프레임
    (추후 확장 가능)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # 추후 구현
        pass


class AuditTable(QFrame):
    """로직 감사 테이블 컨테이너

    감사 로그 테이블을 포함한 프레임
    (추후 확장 가능)
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        # 추후 구현
        pass
