"""
Fallback 디자인 토큰 (SSOT 임포트 실패 시 사용)

Issue #2 Fix (v7.27): 타입 안전성 및 완전성 보장
- type: ignore 제거
- SSOT와 동일한 인터페이스 제공
- 중복 fallback 제거 (DRY 원칙)

사용처:
- ui/widgets/backtest/single.py
- ui/widgets/trading/live_multi.py
- 기타 UI 컴포넌트
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ColorTokensFallback:
    """Colors 토큰 Fallback (SSOT 동일 인터페이스)"""

    # === Background Colors ===
    bg_base: str = "#0d1117"
    bg_surface: str = "#161b22"
    bg_elevated: str = "#1f2937"
    bg_overlay: str = "#30363d"

    # === Text Colors ===
    text_primary: str = "#f0f6fc"
    text_secondary: str = "#8b949e"
    text_muted: str = "#6e7681"
    text_disabled: str = "#484f58"

    # === Brand Colors ===
    primary: str = "#58a6ff"
    secondary: str = "#8b949e"
    accent_primary: str = "#00d4ff"
    accent_secondary: str = "#ff9800"

    # === Semantic Colors ===
    success: str = "#3fb950"
    warning: str = "#d29922"
    danger: str = "#f85149"
    info: str = "#58a6ff"

    # === Border Colors ===
    border_default: str = "#30363d"
    border_muted: str = "#21262d"
    border_subtle: str = "#161b22"

    # === Interactive States ===
    hover: str = "#1f6feb"
    active: str = "#1158c7"
    focus: str = "#58a6ff"

    # === Grade Colors ===
    grade_s: str = "#ffd700"
    grade_a: str = "#3fb950"
    grade_b: str = "#58a6ff"
    grade_c: str = "#8b949e"
    grade_f: str = "#f85149"

    # === Financial Colors ===
    profit: str = "#26a69a"
    loss: str = "#ef5350"


@dataclass(frozen=True)
class TypographyTokensFallback:
    """Typography 토큰 Fallback"""

    # === Font Family ===
    font_sans: str = "'Pretendard', 'Inter', 'Segoe UI', sans-serif"
    font_mono: str = "'JetBrains Mono', 'Consolas', monospace"

    # === Font Size ===
    text_xs: str = "11px"
    text_sm: str = "12px"
    text_base: str = "14px"
    text_lg: str = "16px"
    text_xl: str = "18px"
    text_2xl: str = "24px"
    text_3xl: str = "28px"
    text_4xl: str = "32px"

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


@dataclass(frozen=True)
class SpacingTokensFallback:
    """Spacing 토큰 Fallback"""

    # === CSS String Values ===
    space_0: str = "0px"
    space_1: str = "4px"
    space_2: str = "8px"
    space_3: str = "12px"
    space_4: str = "16px"
    space_5: str = "20px"
    space_6: str = "24px"
    space_8: str = "32px"
    space_10: str = "40px"
    space_12: str = "48px"
    space_16: str = "64px"

    # === Integer Values for PyQt ===
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


@dataclass(frozen=True)
class RadiusTokensFallback:
    """Radius 토큰 Fallback"""

    radius_none: str = "0px"
    radius_sm: str = "2px"
    radius_md: str = "4px"
    radius_lg: str = "8px"
    radius_xl: str = "12px"
    radius_full: str = "9999px"


@dataclass(frozen=True)
class SizeTokensFallback:
    """Size 토큰 Fallback"""

    # === Button Heights ===
    button_sm: int = 32
    button_md: int = 36
    button_lg: int = 40

    # === Card Heights ===
    card_compact: int = 60
    card_normal: int = 80
    card_large: int = 100

    # === Input Widths ===
    control_min_width: int = 120
    input_min_width: int = 200
    button_min_width: int = 80
    slider_min_width: int = 200  # Issue #3
    label_min_width: int = 100   # Issue #3


# 싱글톤 인스턴스 (모든 fallback에서 공유)
Colors = ColorTokensFallback()
Typography = TypographyTokensFallback()
Spacing = SpacingTokensFallback()
Radius = RadiusTokensFallback()
Size = SizeTokensFallback()
