"""
TwinStar Quantum Design System
==============================

통합 디자인 시스템 - Single Source of Truth
PyQt5 의존성 없이 디자인 토큰만 사용 가능

사용법:
    from ui.design_system import Colors, Typography, Spacing, Radius
    from ui.design_system import ThemeGenerator
    
    # 색상 사용
    bg = Colors.bg_base  # "#0d1117"
    
    # 테마 적용 (PyQt5 환경에서)
    app.setStyleSheet(ThemeGenerator.generate())
"""

# 토큰은 항상 사용 가능 (순수 Python)
from .tokens import (
    Colors,
    Typography, 
    Spacing,
    Radius,
    Shadow,
    get_gradient,
    get_grade_color,
)

# ThemeGenerator는 순수 문자열 생성기이므로 항상 사용 가능
from .theme import ThemeGenerator, ComponentStyles

__all__ = [
    # 토큰
    'Colors',
    'Typography',
    'Spacing',
    'Radius',
    'Shadow',
    
    # 유틸리티
    'get_gradient',
    'get_grade_color',
    
    # 테마
    'ThemeGenerator',
    'ComponentStyles',
]

__version__ = '1.0.0'
