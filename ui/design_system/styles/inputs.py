"""
TwinStar Quantum - Input Styles
===============================

입력 컴포넌트 스타일
"""

from ..tokens import Colors, Typography, Spacing, Radius


class InputStyles:
    """
    입력 필드 스타일 생성기
    
    사용법:
        line_edit.setStyleSheet(InputStyles.default())
        combo_box.setStyleSheet(InputStyles.combo())
    """
    
    @staticmethod
    def default() -> str:
        """기본 입력 필드 (QLineEdit, QSpinBox, QDoubleSpinBox)"""
        return f"""
            QLineEdit, QSpinBox, QDoubleSpinBox {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_2} {Spacing.space_3};
                font-size: {Typography.text_base};
                min-height: 36px;
                selection-background-color: {Colors.accent_primary};
                selection-color: {Colors.text_inverse};
            }}
            QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover {{
                border-color: {Colors.text_secondary};
            }}
            QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
                border: 2px solid {Colors.border_accent};
                background-color: {Colors.bg_base};
            }}
            QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
                background-color: {Colors.bg_surface};
                color: {Colors.text_muted};
            }}
        """
    
    @staticmethod
    def combo() -> str:
        """콤보박스 스타일"""
        return f"""
            QComboBox {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_2} {Spacing.space_3};
                min-height: 36px;
                font-size: {Typography.text_base};
            }}
            QComboBox:hover {{
                border-color: {Colors.text_secondary};
            }}
            QComboBox:focus {{
                border: 2px solid {Colors.border_accent};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 30px;
                subcontrol-origin: padding;
                subcontrol-position: right center;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {Colors.text_secondary};
                margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.bg_surface};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_sm};
                selection-background-color: {Colors.accent_primary};
                selection-color: {Colors.text_inverse};
                outline: none;
                padding: {Spacing.space_1};
            }}
            QComboBox QAbstractItemView::item {{
                padding: {Spacing.space_2} {Spacing.space_3};
                min-height: 32px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {Colors.bg_overlay};
            }}
        """
    
    @staticmethod
    def checkbox() -> str:
        """체크박스 스타일"""
        return f"""
            QCheckBox {{
                color: {Colors.text_primary};
                spacing: {Spacing.space_2};
                font-size: {Typography.text_base};
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: {Radius.radius_sm};
                border: 2px solid {Colors.border_default};
                background: {Colors.bg_elevated};
            }}
            QCheckBox::indicator:hover {{
                border-color: {Colors.accent_primary};
            }}
            QCheckBox::indicator:checked {{
                background-color: {Colors.accent_primary};
                border-color: {Colors.accent_primary};
            }}
            QCheckBox::indicator:disabled {{
                background-color: {Colors.bg_surface};
                border-color: {Colors.border_muted};
            }}
        """
    
    @staticmethod
    def radio() -> str:
        """라디오 버튼 스타일"""
        return f"""
            QRadioButton {{
                color: {Colors.text_primary};
                spacing: {Spacing.space_2};
                font-size: {Typography.text_base};
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid {Colors.border_default};
                background: {Colors.bg_elevated};
            }}
            QRadioButton::indicator:hover {{
                border-color: {Colors.accent_primary};
            }}
            QRadioButton::indicator:checked {{
                background-color: {Colors.accent_primary};
                border-color: {Colors.accent_primary};
            }}
            QRadioButton::indicator:disabled {{
                background-color: {Colors.bg_surface};
                border-color: {Colors.border_muted};
            }}
        """
    
    @staticmethod
    def search() -> str:
        """검색 입력 필드"""
        return f"""
            QLineEdit {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_lg};
                padding: {Spacing.space_2} {Spacing.space_4};
                padding-left: 32px;
                font-size: {Typography.text_base};
                min-height: 40px;
            }}
            QLineEdit:focus {{
                border: 2px solid {Colors.border_accent};
                background-color: {Colors.bg_base};
            }}
        """
    
    @staticmethod
    def text_area() -> str:
        """멀티라인 텍스트 입력"""
        return f"""
            QTextEdit, QPlainTextEdit {{
                background-color: {Colors.bg_elevated};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_3};
                font-size: {Typography.text_base};
                selection-background-color: {Colors.accent_primary};
                selection-color: {Colors.text_inverse};
            }}
            QTextEdit:focus, QPlainTextEdit:focus {{
                border: 2px solid {Colors.border_accent};
            }}
        """
    
    @staticmethod
    def log_viewer() -> str:
        """로그 뷰어 (읽기 전용, 모노스페이스)"""
        return f"""
            QTextEdit, QPlainTextEdit {{
                background-color: {Colors.terminal_bg};
                color: {Colors.terminal_green};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_md};
                font-family: {Typography.font_mono};
                font-size: {Typography.text_sm};
                padding: {Spacing.space_2};
                selection-background-color: {Colors.accent_primary};
                selection-color: {Colors.text_inverse};
            }}
        """
