"""
TwinStar Quantum Design Tokens
==============================

모든 디자인 값의 Single Source of Truth (SSOT)

이 파일만 수정하면 전체 앱의 디자인이 변경됩니다.

사용법:
    from ui.design_system.tokens import Colors, Typography, Spacing
    
    # 색상
    background = Colors.bg_base
    accent = Colors.accent_primary
    
    # 폰트
    font = Typography.font_sans
    size = Typography.text_base
    
    # 간격
    padding = Spacing.space_4
"""

from dataclasses import dataclass
from typing import Optional


# ============================================================
# COLOR TOKENS
# ============================================================

@dataclass(frozen=True)
class ColorTokens:
    """
    색상 토큰 정의
    
    기존 테마에서 통합:
    - GUI/styles/theme.py (Theme)
    - GUI/styles/premium_theme.py (PremiumTheme)
    - GUI/styles/elegant_theme.py (ElegantTheme)
    - GUI/styles/vivid_theme.py (VividTheme)
    - GUI/legacy_styles.py (COLORS)
    """
    
    # === Background Scale ===
    # 어두운 순서: base → surface → elevated → overlay
    bg_base: str = "#0d1117"      # 최상위 배경 (가장 어두움)
    bg_surface: str = "#161b22"   # 카드/패널 배경
    bg_elevated: str = "#21262d"  # 입력 필드, 높은 요소
    bg_overlay: str = "#30363d"   # 호버, 드롭다운 (가장 밝음)
    
    # === Text Scale ===
    text_primary: str = "#f0f6fc"    # 기본 텍스트 (밝음)
    text_secondary: str = "#8b949e"  # 보조 텍스트
    text_muted: str = "#484f58"      # 비활성/힌트 텍스트
    text_inverse: str = "#0d1117"    # 밝은 배경용 텍스트
    
    # === Brand / Accent ===
    accent_primary: str = "#00d4aa"    # 메인 민트 (브랜드 컬러)
    accent_secondary: str = "#58a6ff"  # 보조 블루
    accent_hover: str = "#00e6b8"      # 민트 호버
    accent_pressed: str = "#00b894"    # 민트 pressed
    
    # === Semantic Colors ===
    success: str = "#3fb950"       # 수익/성공/매수
    success_bg: str = "#0d2818"    # 성공 배경
    danger: str = "#f85149"        # 손실/위험/매도
    danger_bg: str = "#2d1214"     # 위험 배경
    warning: str = "#d29922"       # 경고
    warning_bg: str = "#2d2305"    # 경고 배경
    info: str = "#58a6ff"          # 정보
    info_bg: str = "#0d1d30"       # 정보 배경
    
    # === Border ===
    border_default: str = "#30363d"   # 기본 테두리
    border_muted: str = "#21262d"     # 은은한 테두리
    border_accent: str = "#00d4aa"    # 강조 테두리 (포커스)
    
    # === Special ===
    terminal_green: str = "#00ff00"   # 로그창 텍스트
    terminal_bg: str = "#000000"      # 로그창 배경
    
    # === Grade Colors (라이선스 등급) ===
    grade_trial: str = "#787b86"
    grade_basic: str = "#2196f3"
    grade_standard: str = "#ff9800"
    grade_premium: str = "#00e676"
    grade_expired: str = "#ef5350"


# ============================================================
# TYPOGRAPHY TOKENS
# ============================================================

@dataclass(frozen=True)
class TypographyTokens:
    """
    타이포그래피 토큰 정의
    
    폰트 우선순위:
    1. Pretendard - 한글/영문 최적화
    2. Inter - 숫자 가독성 우수
    3. Segoe UI - Windows 기본
    4. Apple SD Gothic Neo - macOS 기본
    """
    
    # === Font Family ===
    font_sans: str = "'Pretendard', 'Inter', 'Segoe UI', 'Apple SD Gothic Neo', sans-serif"
    font_mono: str = "'JetBrains Mono', 'Fira Code', 'D2Coding', 'Consolas', monospace"
    
    # === Font Size ===
    text_xs: str = "11px"     # 아주 작은 텍스트
    text_sm: str = "12px"     # 작은 텍스트, 라벨
    text_base: str = "14px"   # 기본 텍스트
    text_lg: str = "16px"     # 큰 텍스트
    text_xl: str = "18px"     # 제목
    text_2xl: str = "24px"    # 큰 제목
    text_3xl: str = "28px"    # 메인 숫자/제목
    text_4xl: str = "32px"    # 히어로 텍스트
    
    # === Font Weight ===
    font_normal: int = 400
    font_medium: int = 500
    font_semibold: int = 600
    font_bold: int = 700
    font_extrabold: int = 800
    
    # === Line Height ===
    leading_tight: str = "1.25"
    leading_normal: str = "1.5"
    leading_relaxed: str = "1.75"
    
    # === Letter Spacing ===
    tracking_tight: str = "-0.5px"
    tracking_normal: str = "0"
    tracking_wide: str = "0.5px"


# ============================================================
# SPACING TOKENS
# ============================================================

@dataclass(frozen=True)
class SpacingTokens:
    """
    간격 토큰 정의
    
    4px 기반 스케일
    """
    
    space_0: str = "0px"
    space_1: str = "4px"      # 최소 간격
    space_2: str = "8px"      # 작은 간격
    space_3: str = "12px"     # 기본 패딩
    space_4: str = "16px"     # 표준 간격
    space_5: str = "20px"
    space_6: str = "24px"     # 큰 간격
    space_8: str = "32px"     # 섹션 간격
    space_10: str = "40px"    # 대형 간격
    space_12: str = "48px"
    space_16: str = "64px"

    # === Integer values for PyQt (px 제거) ===
    i_space_0: int = 0
    i_space_1: int = 4
    i_space_2: int = 8
    i_space_3: int = 12
    i_space_4: int = 16
    i_space_5: int = 20
    i_space_6: int = 24
    i_space_8: int = 32
    i_space_10: int = 40
    i_space_12: int = 48
    i_space_16: int = 64


# ============================================================
# RADIUS TOKENS
# ============================================================

@dataclass(frozen=True)
class RadiusTokens:
    """모서리 반경 토큰"""
    
    radius_none: str = "0px"
    radius_sm: str = "4px"      # 버튼, 입력 필드
    radius_md: str = "8px"      # 카드
    radius_lg: str = "12px"     # 패널, 모달
    radius_xl: str = "16px"     # 대형 카드
    radius_full: str = "9999px" # 원형 (뱃지, 아바타)

    # === Integer values for PyQt ===
    i_radius_none: int = 0
    i_radius_sm: int = 4
    i_radius_md: int = 8
    i_radius_lg: int = 12
    i_radius_xl: int = 16


# ============================================================
# SHADOW TOKENS
# ============================================================

@dataclass(frozen=True)
class ShadowTokens:
    """그림자 토큰"""
    
    shadow_none: str = "none"
    shadow_sm: str = "0 1px 2px rgba(0, 0, 0, 0.3)"
    shadow_md: str = "0 4px 8px rgba(0, 0, 0, 0.4)"
    shadow_lg: str = "0 8px 16px rgba(0, 0, 0, 0.5)"
    shadow_xl: str = "0 12px 24px rgba(0, 0, 0, 0.6)"
    
    # 글로우 효과
    glow_accent: str = "0 0 20px rgba(0, 212, 170, 0.3)"
    glow_success: str = "0 0 20px rgba(63, 185, 80, 0.3)"
    glow_danger: str = "0 0 20px rgba(248, 81, 73, 0.3)"


# ============================================================
# ANIMATION TOKENS
# ============================================================

@dataclass(frozen=True)
class AnimationTokens:
    """애니메이션 토큰"""

    duration_fast: str = "100ms"
    duration_normal: str = "200ms"
    duration_slow: str = "300ms"

    easing_default: str = "ease"
    easing_in: str = "ease-in"
    easing_out: str = "ease-out"
    easing_in_out: str = "ease-in-out"


# ============================================================
# SIZE TOKENS
# ============================================================

@dataclass(frozen=True)
class SizeTokens:
    """
    크기 상수 토큰

    위젯의 고정 크기를 정의합니다.
    하드코딩된 크기 값을 방지하고 일관성을 보장합니다.
    """

    # === Button Heights ===
    button_sm: int = 32      # 작은 버튼
    button_md: int = 36      # 중간 버튼 (기본)
    button_lg: int = 40      # 큰 버튼

    # === Input Field Heights ===
    input_sm: int = 28       # 작은 입력 필드
    input_md: int = 32       # 중간 입력 필드
    input_lg: int = 36       # 큰 입력 필드

    # === Card Heights ===
    card_compact: int = 60   # 압축 카드
    card_normal: int = 80    # 일반 카드 (대시보드 상태 카드)
    card_large: int = 100    # 큰 카드

    # === Minimum Widths ===
    control_min_width: int = 120   # 콤보박스, 작은 입력
    input_min_width: int = 200     # 일반 입력 필드
    button_min_width: int = 80     # 버튼 최소 너비

    # === Component Specific ===
    refresh_button_size: int = 36  # 새로고침 버튼 (정사각형)


# ============================================================
# SINGLETON INSTANCES
# ============================================================

# 전역 싱글톤 인스턴스
Colors = ColorTokens()
Typography = TypographyTokens()
Spacing = SpacingTokens()
Radius = RadiusTokens()
Shadow = ShadowTokens()
Animation = AnimationTokens()
Size = SizeTokens()


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def get_gradient(
    start: Optional[str] = None,
    end: Optional[str] = None,
    direction: str = "horizontal"
) -> str:
    """
    Qt 그라디언트 문자열 생성
    
    Args:
        start: 시작 색상 (기본: accent_primary)
        end: 끝 색상 (기본: accent_pressed)
        direction: 'horizontal' 또는 'vertical'
    
    Returns:
        Qt qlineargradient 문자열
    
    Example:
        >>> get_gradient()
        'qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d4aa, stop:1 #00b894)'
    """
    start = start or Colors.accent_primary
    end = end or Colors.accent_pressed
    
    if direction == "horizontal":
        return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {start}, stop:1 {end})"
    else:
        return f"qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {start}, stop:1 {end})"


def get_rgba(hex_color: str, alpha: float) -> str:
    """
    HEX 색상을 RGBA로 변환
    
    Args:
        hex_color: '#RRGGBB' 형식의 색상
        alpha: 투명도 (0.0 ~ 1.0)
    
    Returns:
        'rgba(r, g, b, a)' 문자열
    
    Example:
        >>> get_rgba('#00d4aa', 0.5)
        'rgba(0, 212, 170, 0.5)'
    """
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def get_pnl_color(value: float) -> str:
    """
    PnL 값에 따른 색상 반환
    
    Args:
        value: PnL 값
    
    Returns:
        수익이면 success, 손실이면 danger 색상
    """
    return Colors.success if value >= 0 else Colors.danger


def get_grade_color(grade: str) -> str:
    """
    등급에 따른 색상 반환

    Args:
        grade: 등급 문자열 (TRIAL, BASIC, STANDARD, PREMIUM, EXPIRED)

    Returns:
        등급별 색상
    """
    grade_colors = {
        'TRIAL': Colors.grade_trial,
        'BASIC': Colors.grade_basic,
        'STANDARD': Colors.grade_standard,
        'PREMIUM': Colors.grade_premium,
        'EXPIRED': Colors.grade_expired,
    }
    return grade_colors.get(grade.upper(), Colors.grade_trial)


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    # Token Classes
    'ColorTokens',
    'TypographyTokens',
    'SpacingTokens',
    'RadiusTokens',
    'ShadowTokens',
    'AnimationTokens',
    'SizeTokens',
    # Singleton Instances
    'Colors',
    'Typography',
    'Spacing',
    'Radius',
    'Shadow',
    'Animation',
    'Size',
    # Utility Functions
    'get_gradient',
    'get_rgba',
    'get_pnl_color',
    'get_grade_color',
]
