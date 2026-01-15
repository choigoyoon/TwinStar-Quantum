"""
백테스트 위젯 스타일 상수

ui.design_system.tokens 기반 스타일 생성기
모든 백테스트 위젯에서 일관된 스타일 사용
"""

from ui.design_system.tokens import ColorTokens

# 토큰 인스턴스
_tokens = ColorTokens()


class BacktestStyles:
    """백테스트 위젯 스타일 상수 (SSOT)"""

    @staticmethod
    def button_primary() -> str:
        """기본 버튼 스타일 (SUCCESS 색상)"""
        return f"""
            QPushButton {{
                background: {_tokens.success};
                color: {_tokens.text_primary};
                padding: 10px 25px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {_tokens.success}cc;
            }}
            QPushButton:disabled {{
                background: {_tokens.bg_overlay};
                color: {_tokens.text_muted};
            }}
        """

    @staticmethod
    def button_danger() -> str:
        """위험 버튼 스타일 (DANGER 색상)"""
        return f"""
            QPushButton {{
                background: {_tokens.danger};
                color: {_tokens.text_primary};
                padding: 10px 25px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {_tokens.danger}cc;
            }}
            QPushButton:disabled {{
                background: {_tokens.bg_overlay};
                color: {_tokens.text_muted};
            }}
        """

    @staticmethod
    def button_info() -> str:
        """정보 버튼 스타일 (INFO 색상)"""
        return f"""
            QPushButton {{
                background: {_tokens.info};
                color: {_tokens.text_primary};
                padding: 10px 25px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {_tokens.info}cc;
            }}
            QPushButton:disabled {{
                background: {_tokens.bg_overlay};
                color: {_tokens.text_muted};
            }}
        """

    @staticmethod
    def button_accent() -> str:
        """강조 버튼 스타일 (ACCENT_PRIMARY 색상)"""
        return f"""
            QPushButton {{
                background: {_tokens.accent_primary};
                color: {_tokens.text_inverse};
                padding: 10px 25px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: {_tokens.accent_hover};
            }}
            QPushButton:disabled {{
                background: {_tokens.bg_overlay};
                color: {_tokens.text_muted};
            }}
        """

    @staticmethod
    def combo_box() -> str:
        """콤보박스 스타일"""
        return f"""
            QComboBox {{
                background: {_tokens.bg_elevated};
                color: {_tokens.text_primary};
                padding: 5px;
                border: 1px solid {_tokens.border_default};
                border-radius: 3px;
            }}
            QComboBox:hover {{
                border: 1px solid {_tokens.border_accent};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {_tokens.bg_elevated};
                color: {_tokens.text_primary};
                selection-background-color: {_tokens.accent_primary};
            }}
        """

    @staticmethod
    def table() -> str:
        """테이블 스타일"""
        return f"""
            QTableWidget {{
                background: {_tokens.bg_surface};
                color: {_tokens.text_primary};
                border: none;
                gridline-color: {_tokens.border_default};
            }}
            QHeaderView::section {{
                background: {_tokens.bg_base};
                color: {_tokens.text_secondary};
                padding: 6px;
                border: 1px solid {_tokens.border_default};
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 4px;
            }}
            QTableWidget::item:selected {{
                background: {_tokens.accent_primary}40;
            }}
        """

    @staticmethod
    def progress_bar() -> str:
        """진행 바 스타일"""
        return f"""
            QProgressBar {{
                border: 1px solid {_tokens.border_default};
                border-radius: 5px;
                text-align: center;
                background: {_tokens.bg_base};
                color: {_tokens.text_primary};
                height: 25px;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background: {_tokens.accent_primary};
                border-radius: 4px;
            }}
        """

    @staticmethod
    def group_box(border_color: str | None = None) -> str:
        """그룹박스 스타일

        Args:
            border_color: 테두리 색상 (기본값: border_default)
        """
        color = border_color or _tokens.border_default
        return f"""
            QGroupBox {{
                border: 1px solid {color};
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                color: {color};
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
            }}
        """

    @staticmethod
    def tab_widget() -> str:
        """탭 위젯 스타일"""
        return f"""
            QTabWidget::pane {{
                border: 1px solid {_tokens.border_default};
                border-radius: 4px;
            }}
            QTabBar::tab {{
                background: {_tokens.bg_elevated};
                color: {_tokens.text_secondary};
                padding: 10px 25px;
                margin-right: 2px;
                font-weight: bold;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {_tokens.bg_overlay};
                color: {_tokens.text_primary};
                border-bottom: 2px solid {_tokens.success};
            }}
            QTabBar::tab:hover {{
                background: {_tokens.bg_overlay};
            }}
        """

    @staticmethod
    def spin_box() -> str:
        """스핀박스 스타일"""
        return f"""
            QSpinBox, QDoubleSpinBox {{
                background: {_tokens.bg_elevated};
                color: {_tokens.text_primary};
                padding: 5px;
                border: 1px solid {_tokens.border_default};
                border-radius: 3px;
            }}
            QSpinBox:hover, QDoubleSpinBox:hover {{
                border: 1px solid {_tokens.border_accent};
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                background: {_tokens.bg_overlay};
                border: none;
            }}
        """

    @staticmethod
    def label_secondary() -> str:
        """보조 라벨 스타일"""
        return f"color: {_tokens.text_secondary}; font-size: 11px;"

    @staticmethod
    def label_primary() -> str:
        """주요 라벨 스타일"""
        return f"color: {_tokens.text_primary}; font-size: 14px; font-weight: bold;"

    @staticmethod
    def label_value(color: str | None = None) -> str:
        """값 표시 라벨 스타일

        Args:
            color: 텍스트 색상 (기본값: text_primary)
        """
        text_color = color or _tokens.text_primary
        return f"color: {text_color}; font-size: 14px; font-weight: bold;"
