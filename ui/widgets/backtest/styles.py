"""
백테스트 위젯 스타일 상수

ui.design_system.tokens 기반 스타일 생성기
모든 백테스트 위젯에서 일관된 스타일 사용
"""

from ui.design_system.tokens import Colors, Typography, Spacing, Radius


class BacktestStyles:
    """백테스트 위젯 스타일 상수 (SSOT)"""

    @staticmethod
    def button_primary() -> str:
        """기본 버튼 스타일 (SUCCESS 색상)"""
        return f"""
            QPushButton {{
                background: {Colors.success};
                color: {Colors.text_primary};
                padding: {Spacing.space_3} {Spacing.space_6};
                border-radius: {Radius.radius_sm};
                font-weight: {Typography.font_bold};
                font-size: {Typography.text_sm};
            }}
            QPushButton:hover {{
                background: {Colors.success}cc;
            }}
            QPushButton:disabled {{
                background: {Colors.bg_overlay};
                color: {Colors.text_muted};
            }}
        """

    @staticmethod
    def button_danger() -> str:
        """위험 버튼 스타일 (DANGER 색상)"""
        return f"""
            QPushButton {{
                background: {Colors.danger};
                color: {Colors.text_primary};
                padding: {Spacing.space_3} {Spacing.space_6};
                border-radius: {Radius.radius_sm};
                font-weight: {Typography.font_bold};
                font-size: {Typography.text_sm};
            }}
            QPushButton:hover {{
                background: {Colors.danger}cc;
            }}
            QPushButton:disabled {{
                background: {Colors.bg_overlay};
                color: {Colors.text_muted};
            }}
        """

    @staticmethod
    def button_info() -> str:
        """정보 버튼 스타일 (INFO 색상)"""
        return f"""
            QPushButton {{
                background: {Colors.info};
                color: {Colors.text_primary};
                padding: {Spacing.space_3} {Spacing.space_6};
                border-radius: {Radius.radius_sm};
                font-weight: {Typography.font_bold};
                font-size: {Typography.text_sm};
            }}
            QPushButton:hover {{
                background: {Colors.info}cc;
            }}
            QPushButton:disabled {{
                background: {Colors.bg_overlay};
                color: {Colors.text_muted};
            }}
        """

    @staticmethod
    def button_accent() -> str:
        """강조 버튼 스타일 (ACCENT_PRIMARY 색상)"""
        return f"""
            QPushButton {{
                background: {Colors.accent_primary};
                color: {Colors.text_inverse};
                padding: {Spacing.space_3} {Spacing.space_6};
                border-radius: {Radius.radius_sm};
                font-weight: {Typography.font_bold};
                font-size: {Typography.text_sm};
            }}
            QPushButton:hover {{
                background: {Colors.accent_hover};
            }}
            QPushButton:disabled {{
                background: {Colors.bg_overlay};
                color: {Colors.text_muted};
            }}
        """

    @staticmethod
    def combo_box() -> str:
        """콤보박스 스타일"""
        return f"""
            QComboBox {{
                background: {Colors.bg_elevated};
                color: {Colors.text_primary};
                padding: {Spacing.space_1};
                border: 1px solid {Colors.border_default};
                border-radius: 3px;
            }}
            QComboBox:hover {{
                border: 1px solid {Colors.border_accent};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background: {Colors.bg_elevated};
                color: {Colors.text_primary};
                selection-background-color: {Colors.accent_primary};
            }}
        """

    @staticmethod
    def table() -> str:
        """테이블 스타일"""
        return f"""
            QTableWidget {{
                background: {Colors.bg_surface};
                color: {Colors.text_primary};
                border: none;
                gridline-color: {Colors.border_default};
            }}
            QHeaderView::section {{
                background: {Colors.bg_base};
                color: {Colors.text_secondary};
                padding: {Spacing.space_2};
                border: 1px solid {Colors.border_default};
                font-weight: {Typography.font_bold};
            }}
            QTableWidget::item {{
                padding: {Spacing.space_1};
            }}
            QTableWidget::item:selected {{
                background: {Colors.accent_primary}40;
            }}
        """

    @staticmethod
    def progress_bar() -> str:
        """진행 바 스타일"""
        return f"""
            QProgressBar {{
                border: 1px solid {Colors.border_default};
                border-radius: 5px;
                text-align: center;
                background: {Colors.bg_base};
                color: {Colors.text_primary};
                height: 25px;
                font-weight: {Typography.font_bold};
            }}
            QProgressBar::chunk {{
                background: {Colors.accent_primary};
                border-radius: {Radius.radius_sm};
            }}
        """

    @staticmethod
    def group_box(border_color: str | None = None) -> str:
        """그룹박스 스타일

        Args:
            border_color: 테두리 색상 (기본값: border_default)
        """
        color = border_color or Colors.border_default
        return f"""
            QGroupBox {{
                border: 1px solid {color};
                border-radius: 5px;
                margin-top: {Spacing.space_3};
                font-weight: {Typography.font_bold};
                color: {color};
                padding-top: {Spacing.space_3};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: {Spacing.space_0} {Spacing.space_1};
            }}
        """

    @staticmethod
    def tab_widget() -> str:
        """탭 위젯 스타일"""
        return f"""
            QTabWidget::pane {{
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_sm};
            }}
            QTabBar::tab {{
                background: {Colors.bg_elevated};
                color: {Colors.text_secondary};
                padding: {Spacing.space_3} {Spacing.space_6};
                margin-right: {Spacing.space_0};
                font-weight: {Typography.font_bold};
                border-top-left-radius: {Radius.radius_sm};
                border-top-right-radius: {Radius.radius_sm};
            }}
            QTabBar::tab:selected {{
                background: {Colors.bg_overlay};
                color: {Colors.text_primary};
                border-bottom: 2px solid {Colors.success};
            }}
            QTabBar::tab:hover {{
                background: {Colors.bg_overlay};
            }}
        """

    @staticmethod
    def spin_box() -> str:
        """스핀박스 스타일"""
        return f"""
            QSpinBox, QDoubleSpinBox {{
                background: {Colors.bg_elevated};
                color: {Colors.text_primary};
                padding: {Spacing.space_1};
                border: 1px solid {Colors.border_default};
                border-radius: 3px;
            }}
            QSpinBox:hover, QDoubleSpinBox:hover {{
                border: 1px solid {Colors.border_accent};
            }}
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {{
                background: {Colors.bg_overlay};
                border: none;
            }}
        """

    @staticmethod
    def label_secondary() -> str:
        """보조 라벨 스타일"""
        return f"color: {Colors.text_secondary}; font-size: {Typography.text_xs};"

    @staticmethod
    def label_primary() -> str:
        """주요 라벨 스타일"""
        return f"color: {Colors.text_primary}; font-size: {Typography.text_base}; font-weight: {Typography.font_bold};"

    @staticmethod
    def label_value(color: str | None = None) -> str:
        """값 표시 라벨 스타일

        Args:
            color: 텍스트 색상 (기본값: text_primary)
        """
        text_color = color or Colors.text_primary
        return f"color: {text_color}; font-size: {Typography.text_base}; font-weight: {Typography.font_bold};"
