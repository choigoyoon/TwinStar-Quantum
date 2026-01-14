"""
GUI/styles - Legacy Theme System
================================

[DEPRECATED] 이 패키지는 ui.design_system으로 대체되었습니다.

마이그레이션 가이드:
    # Before (deprecated)
    from GUI.styles import Theme
    app.setStyleSheet(Theme.get_stylesheet())
    
    # After (recommended)
    from ui.design_system import ThemeGenerator
    app.setStyleSheet(ThemeGenerator.generate())

이 패키지는 호환성을 위해 유지되지만, 
새 코드에서는 ui.design_system을 사용하세요.
"""

import warnings

# 레거시 import 유지 (호환성)
from .theme import Theme
from .premium_theme import PremiumTheme
from .fonts import FontSystem


def _show_deprecation_warning():
    warnings.warn(
        "GUI.styles is deprecated. Use ui.design_system instead. "
        "See docs/UI_DESIGN_SYSTEM.md for migration guide.",
        DeprecationWarning,
        stacklevel=3
    )


# 기존 Theme 클래스 래핑 (경고 추가)
class DeprecatedTheme(Theme):
    """[DEPRECATED] Use ui.design_system.ThemeGenerator instead"""
    
    @classmethod
    def get_stylesheet(cls) -> str:
        _show_deprecation_warning()
        return super().get_stylesheet()


__all__ = [
    'Theme',
    'PremiumTheme',
    'FontSystem',
    'DeprecatedTheme',
]
