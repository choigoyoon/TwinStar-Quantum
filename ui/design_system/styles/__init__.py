"""
TwinStar Quantum - Component Styles
===================================

컴포넌트별 스타일 모듈

사용법:
    from ui.design_system.styles import ButtonStyles, InputStyles, CardStyles
    
    # 버튼 스타일
    style = ButtonStyles.primary()
    style = ButtonStyles.danger()
    
    # 카드 스타일
    style = CardStyles.status_card()
    style = CardStyles.pnl_card(is_profit=True)
"""

from .buttons import ButtonStyles
from .inputs import InputStyles
from .cards import CardStyles
from .tables import TableStyles
from .dialogs import DialogStyles

__all__ = [
    'ButtonStyles',
    'InputStyles',
    'CardStyles',
    'TableStyles',
    'DialogStyles',
]
