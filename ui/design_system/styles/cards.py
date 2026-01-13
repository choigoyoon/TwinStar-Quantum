"""
TwinStar Quantum - Card Styles
==============================

카드 컴포넌트 스타일
"""

from ..tokens import Colors, Typography, Spacing, Radius, Shadow


class CardStyles:
    """
    카드 스타일 생성기
    
    사용법:
        frame.setStyleSheet(CardStyles.default())
        frame.setStyleSheet(CardStyles.status_card())
    """
    
    @staticmethod
    def default() -> str:
        """기본 카드"""
        return f"""
            QFrame {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_lg};
                padding: {Spacing.space_4};
            }}
            QFrame:hover {{
                border-color: {Colors.text_secondary};
            }}
        """
    
    @staticmethod
    def status_card(accent_color: str = None) -> str:
        """상태 카드 (대시보드용)"""
        accent = accent_color or Colors.accent_primary
        
        return f"""
            QFrame {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_lg};
            }}
            QFrame:hover {{
                border-color: {accent};
            }}
            QLabel#title {{
                color: {Colors.text_secondary};
                font-size: {Typography.text_sm};
                font-weight: {Typography.font_medium};
            }}
            QLabel#value {{
                color: {Colors.text_primary};
                font-size: {Typography.text_2xl};
                font-weight: {Typography.font_bold};
            }}
        """
    
    @staticmethod
    def pnl_card(is_profit: bool = True) -> str:
        """PnL 카드 (수익/손실 표시)"""
        if is_profit:
            accent = Colors.success
            bg = Colors.success_bg
        else:
            accent = Colors.danger
            bg = Colors.danger_bg
        
        return f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {accent};
                border-radius: {Radius.radius_lg};
            }}
            QLabel#value {{
                color: {accent};
                font-size: {Typography.text_2xl};
                font-weight: {Typography.font_bold};
            }}
            QLabel#title {{
                color: {Colors.text_secondary};
                font-size: {Typography.text_sm};
            }}
        """
    
    @staticmethod
    def metric_card() -> str:
        """메트릭 카드 (숫자 강조)"""
        return f"""
            QFrame {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_3};
            }}
            QLabel#metric-label {{
                color: {Colors.text_secondary};
                font-size: {Typography.text_xs};
                font-weight: {Typography.font_medium};
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            QLabel#metric-value {{
                color: {Colors.text_primary};
                font-size: {Typography.text_xl};
                font-weight: {Typography.font_bold};
            }}
        """
    
    @staticmethod
    def info_card() -> str:
        """정보 카드 (파란색 강조)"""
        return f"""
            QFrame {{
                background-color: {Colors.info_bg};
                border: 1px solid {Colors.info};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_3};
            }}
            QLabel {{
                color: {Colors.text_primary};
            }}
        """
    
    @staticmethod
    def warning_card() -> str:
        """경고 카드 (노란색 강조)"""
        return f"""
            QFrame {{
                background-color: {Colors.warning_bg};
                border: 1px solid {Colors.warning};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_3};
            }}
            QLabel {{
                color: {Colors.text_primary};
            }}
        """
    
    @staticmethod
    def danger_card() -> str:
        """위험 카드 (빨간색 강조)"""
        return f"""
            QFrame {{
                background-color: {Colors.danger_bg};
                border: 1px solid {Colors.danger};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_3};
            }}
            QLabel {{
                color: {Colors.text_primary};
            }}
        """
    
    @staticmethod
    def success_card() -> str:
        """성공 카드 (초록색 강조)"""
        return f"""
            QFrame {{
                background-color: {Colors.success_bg};
                border: 1px solid {Colors.success};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_3};
            }}
            QLabel {{
                color: {Colors.text_primary};
            }}
        """
    
    @staticmethod
    def group_box() -> str:
        """그룹박스 스타일"""
        return f"""
            QGroupBox {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_lg};
                margin-top: {Spacing.space_6};
                padding: {Spacing.space_4};
                padding-top: {Spacing.space_6};
                font-weight: {Typography.font_semibold};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: {Spacing.space_4};
                padding: 0 {Spacing.space_2};
                color: {Colors.accent_primary};
                font-size: {Typography.text_base};
                font-weight: {Typography.font_semibold};
                background-color: {Colors.bg_base};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_sm};
            }}
        """
    
    @staticmethod
    def elevated() -> str:
        """그림자가 있는 높은 카드"""
        return f"""
            QFrame {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_lg};
                padding: {Spacing.space_4};
            }}
        """
