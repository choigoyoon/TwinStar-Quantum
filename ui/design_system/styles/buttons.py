"""
TwinStar Quantum - Button Styles
================================

버튼 컴포넌트 스타일
"""

from ..tokens import Colors, Typography, Spacing, Radius, get_gradient


class ButtonStyles:
    """
    버튼 스타일 생성기
    
    사용법:
        button.setStyleSheet(ButtonStyles.primary())
        button.setStyleSheet(ButtonStyles.danger())
    """
    
    @staticmethod
    def primary(size: str = "md") -> str:
        """Primary 버튼 (민트 그라디언트)"""
        padding = _get_padding(size)
        font_size = _get_font_size(size)
        
        return f"""
            QPushButton {{
                background: {get_gradient()};
                color: {Colors.text_inverse};
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {padding};
                font-size: {font_size};
                font-weight: {Typography.font_semibold};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background: {Colors.accent_hover};
            }}
            QPushButton:pressed {{
                background: {Colors.accent_pressed};
            }}
            QPushButton:disabled {{
                background: {Colors.bg_elevated};
                color: {Colors.text_muted};
            }}
        """
    
    @staticmethod
    def danger(size: str = "md") -> str:
        """Danger 버튼 (빨강)"""
        padding = _get_padding(size)
        font_size = _get_font_size(size)
        
        return f"""
            QPushButton {{
                background: {Colors.danger};
                color: white;
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {padding};
                font-size: {font_size};
                font-weight: {Typography.font_semibold};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background: #ff6b6b;
            }}
            QPushButton:pressed {{
                background: #e53935;
            }}
            QPushButton:disabled {{
                background: {Colors.bg_elevated};
                color: {Colors.text_muted};
            }}
        """
    
    @staticmethod
    def success(size: str = "md") -> str:
        """Success 버튼 (초록)"""
        padding = _get_padding(size)
        font_size = _get_font_size(size)
        
        return f"""
            QPushButton {{
                background: {Colors.success};
                color: white;
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {padding};
                font-size: {font_size};
                font-weight: {Typography.font_semibold};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background: #4caf50;
            }}
            QPushButton:pressed {{
                background: #388e3c;
            }}
            QPushButton:disabled {{
                background: {Colors.bg_elevated};
                color: {Colors.text_muted};
            }}
        """
    
    @staticmethod
    def secondary(size: str = "md") -> str:
        """Secondary 버튼 (아웃라인)"""
        padding = _get_padding(size)
        font_size = _get_font_size(size)
        
        return f"""
            QPushButton {{
                background: {Colors.bg_elevated};
                color: {Colors.text_primary};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_sm};
                padding: {padding};
                font-size: {font_size};
                font-weight: {Typography.font_medium};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background: {Colors.bg_overlay};
                border-color: {Colors.border_accent};
            }}
            QPushButton:pressed {{
                background: {Colors.bg_surface};
            }}
            QPushButton:disabled {{
                background: {Colors.bg_surface};
                color: {Colors.text_muted};
                border-color: {Colors.border_muted};
            }}
        """
    
    @staticmethod
    def ghost(size: str = "md") -> str:
        """Ghost 버튼 (투명 배경)"""
        padding = _get_padding(size)
        font_size = _get_font_size(size)
        
        return f"""
            QPushButton {{
                background: transparent;
                color: {Colors.text_primary};
                border: none;
                border-radius: {Radius.radius_sm};
                padding: {padding};
                font-size: {font_size};
                font-weight: {Typography.font_medium};
                min-height: 36px;
            }}
            QPushButton:hover {{
                background: {Colors.bg_overlay};
            }}
            QPushButton:pressed {{
                background: {Colors.bg_elevated};
            }}
            QPushButton:disabled {{
                color: {Colors.text_muted};
            }}
        """
    
    @staticmethod
    def icon(size: int = 32) -> str:
        """아이콘 버튼 (정사각형)"""
        return f"""
            QPushButton {{
                background: transparent;
                color: {Colors.text_secondary};
                border: none;
                border-radius: {size // 2}px;
                min-width: {size}px;
                max-width: {size}px;
                min-height: {size}px;
                max-height: {size}px;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {Colors.bg_overlay};
                color: {Colors.text_primary};
            }}
            QPushButton:pressed {{
                background: {Colors.bg_elevated};
            }}
        """


def _get_padding(size: str) -> str:
    """사이즈에 따른 패딩"""
    paddings = {
        "sm": f"{Spacing.space_1} {Spacing.space_3}",
        "md": f"{Spacing.space_2} {Spacing.space_4}",
        "lg": f"{Spacing.space_3} {Spacing.space_6}",
    }
    return paddings.get(size, paddings["md"])


def _get_font_size(size: str) -> str:
    """사이즈에 따른 폰트 크기"""
    sizes = {
        "sm": Typography.text_sm,
        "md": Typography.text_base,
        "lg": Typography.text_lg,
    }
    return sizes.get(size, sizes["md"])
