"""
UI Design System 테스트
=======================

새 디자인 시스템이 올바르게 작동하는지 검증합니다.
PyQt5 없이도 토큰과 테마 생성이 가능해야 합니다.
"""

import unittest
import sys
import os

# 프로젝트 루트 경로 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)


def load_module(module_name, file_path):
    """PyQt5 의존성 없이 모듈 직접 로드"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# 디자인 시스템 모듈 로드
TOKENS_PATH = os.path.join(PROJECT_ROOT, "ui/design_system/tokens.py")
THEME_PATH = os.path.join(PROJECT_ROOT, "ui/design_system/theme.py")

tokens_module = load_module("tokens", TOKENS_PATH)

# tokens 모듈에서 필요한 것들 추출
Colors = tokens_module.Colors
Typography = tokens_module.Typography
Spacing = tokens_module.Spacing
Radius = tokens_module.Radius
Shadow = tokens_module.Shadow
get_gradient = tokens_module.get_gradient
get_rgba = tokens_module.get_rgba
get_pnl_color = tokens_module.get_pnl_color
get_grade_color = tokens_module.get_grade_color


class TestDesignTokens(unittest.TestCase):
    """디자인 토큰 테스트"""
    
    def test_color_tokens_exist(self):
        """색상 토큰 존재 확인"""
        self.assertIsNotNone(Colors)
        self.assertTrue(hasattr(Colors, 'bg_base'))
        self.assertTrue(hasattr(Colors, 'accent_primary'))
    
    def test_color_tokens_values(self):
        """색상 토큰 값 테스트"""
        # 기본 색상 검증
        self.assertEqual(Colors.bg_base, "#0d1117")
        self.assertEqual(Colors.bg_surface, "#161b22")
        self.assertEqual(Colors.accent_primary, "#00d4aa")
        self.assertEqual(Colors.text_primary, "#f0f6fc")
        
        # 시맨틱 색상 검증
        self.assertEqual(Colors.success, "#3fb950")
        self.assertEqual(Colors.danger, "#f85149")
        self.assertEqual(Colors.warning, "#d29922")
    
    def test_typography_tokens(self):
        """타이포그래피 토큰 테스트"""
        self.assertIn("Pretendard", Typography.font_sans)
        self.assertIn("JetBrains Mono", Typography.font_mono)
        self.assertEqual(Typography.text_base, "14px")
        self.assertEqual(Typography.font_semibold, 600)
    
    def test_spacing_tokens(self):
        """간격 토큰 테스트"""
        self.assertEqual(Spacing.space_0, "0px")
        self.assertEqual(Spacing.space_4, "16px")
        self.assertEqual(Spacing.space_8, "32px")
    
    def test_radius_tokens(self):
        """모서리 토큰 테스트"""
        self.assertEqual(Radius.radius_sm, "4px")
        self.assertEqual(Radius.radius_md, "8px")
        self.assertEqual(Radius.radius_lg, "12px")
    
    def test_shadow_tokens(self):
        """그림자 토큰 테스트"""
        self.assertIn("rgba", Shadow.shadow_sm)
        self.assertIn("rgba", Shadow.shadow_lg)
    
    def test_frozen_dataclass(self):
        """토큰 불변성 테스트"""
        with self.assertRaises((AttributeError, TypeError)):
            Colors.bg_base = "#ffffff"


class TestUtilityFunctions(unittest.TestCase):
    """유틸리티 함수 테스트"""
    
    def test_get_gradient_default(self):
        """기본 그라디언트 생성 테스트"""
        gradient = get_gradient()
        
        self.assertIn("qlineargradient", gradient)
        self.assertIn(Colors.accent_primary, gradient)
        self.assertIn(Colors.accent_pressed, gradient)
    
    def test_get_gradient_horizontal(self):
        """가로 그라디언트 테스트"""
        gradient = get_gradient(direction="horizontal")
        
        self.assertIn("x2:1", gradient)  # horizontal
        self.assertIn("y2:0", gradient)
    
    def test_get_gradient_vertical(self):
        """세로 그라디언트 테스트"""
        gradient = get_gradient(direction="vertical")
        
        self.assertIn("x2:0", gradient)  # vertical
        self.assertIn("y2:1", gradient)
    
    def test_get_gradient_custom_colors(self):
        """커스텀 색상 그라디언트 테스트"""
        gradient = get_gradient("#ff0000", "#00ff00")
        
        self.assertIn("#ff0000", gradient)
        self.assertIn("#00ff00", gradient)
    
    def test_get_rgba(self):
        """RGBA 변환 테스트"""
        rgba = get_rgba("#00d4aa", 0.5)
        self.assertEqual(rgba, "rgba(0, 212, 170, 0.5)")
        
        rgba2 = get_rgba("#ffffff", 1.0)
        self.assertEqual(rgba2, "rgba(255, 255, 255, 1.0)")
        
        rgba3 = get_rgba("#000000", 0)
        self.assertEqual(rgba3, "rgba(0, 0, 0, 0)")
    
    def test_get_pnl_color_profit(self):
        """PnL 색상 - 수익"""
        self.assertEqual(get_pnl_color(100), Colors.success)
        self.assertEqual(get_pnl_color(0.01), Colors.success)
        self.assertEqual(get_pnl_color(0), Colors.success)  # 0은 수익으로
    
    def test_get_pnl_color_loss(self):
        """PnL 색상 - 손실"""
        self.assertEqual(get_pnl_color(-50), Colors.danger)
        self.assertEqual(get_pnl_color(-0.01), Colors.danger)
    
    def test_get_grade_color_all_grades(self):
        """모든 등급 색상 테스트"""
        self.assertEqual(get_grade_color("TRIAL"), Colors.grade_trial)
        self.assertEqual(get_grade_color("BASIC"), Colors.grade_basic)
        self.assertEqual(get_grade_color("STANDARD"), Colors.grade_standard)
        self.assertEqual(get_grade_color("PREMIUM"), Colors.grade_premium)
        self.assertEqual(get_grade_color("EXPIRED"), Colors.grade_expired)
    
    def test_get_grade_color_case_insensitive(self):
        """등급 색상 대소문자 무관"""
        self.assertEqual(get_grade_color("premium"), Colors.grade_premium)
        self.assertEqual(get_grade_color("Premium"), Colors.grade_premium)
        self.assertEqual(get_grade_color("PREMIUM"), Colors.grade_premium)
    
    def test_get_grade_color_unknown(self):
        """알 수 없는 등급 fallback"""
        self.assertEqual(get_grade_color("UNKNOWN"), Colors.grade_trial)
        self.assertEqual(get_grade_color(""), Colors.grade_trial)


class TestThemeGenerator(unittest.TestCase):
    """테마 생성기 테스트"""
    
    @classmethod
    def setUpClass(cls):
        """테마 모듈 로드"""
        # theme.py는 tokens를 import하므로 sys.modules에 추가
        sys.modules['ui.design_system.tokens'] = tokens_module
        cls.theme_module = load_module("theme", THEME_PATH)
        cls.ThemeGenerator = cls.theme_module.ThemeGenerator
        cls.ComponentStyles = cls.theme_module.ComponentStyles
    
    def test_generate_returns_string(self):
        """스타일시트가 문자열인지 확인"""
        stylesheet = self.ThemeGenerator.generate()
        self.assertIsInstance(stylesheet, str)
    
    def test_generate_has_minimum_length(self):
        """충분한 스타일이 생성되었는지"""
        stylesheet = self.ThemeGenerator.generate()
        self.assertGreater(len(stylesheet), 5000)
    
    def test_generate_contains_widgets(self):
        """주요 위젯 스타일 포함 확인"""
        stylesheet = self.ThemeGenerator.generate()
        
        widgets = [
            "QWidget",
            "QPushButton",
            "QLineEdit",
            "QComboBox",
            "QTableWidget",
            "QTabBar",
            "QGroupBox",
            "QCheckBox",
            "QProgressBar",
            "QScrollBar",
        ]
        
        for widget in widgets:
            self.assertIn(widget, stylesheet, f"{widget} 스타일 누락")
    
    def test_generate_contains_color_tokens(self):
        """스타일시트에 토큰 값 포함 확인"""
        stylesheet = self.ThemeGenerator.generate()
        
        # 주요 색상 토큰 포함 확인
        self.assertIn(Colors.bg_base, stylesheet)
        self.assertIn(Colors.accent_primary, stylesheet)
        self.assertIn(Colors.text_primary, stylesheet)
    
    def test_generate_contains_button_variants(self):
        """버튼 변형 스타일 확인"""
        stylesheet = self.ThemeGenerator.generate()
        
        self.assertIn('variant="danger"', stylesheet)
        self.assertIn('variant="secondary"', stylesheet)
        self.assertIn('variant="ghost"', stylesheet)


class TestComponentStyles(unittest.TestCase):
    """컴포넌트 스타일 헬퍼 테스트"""
    
    @classmethod
    def setUpClass(cls):
        """테마 모듈 로드"""
        sys.modules['ui.design_system.tokens'] = tokens_module
        cls.theme_module = load_module("theme", THEME_PATH)
        cls.ComponentStyles = cls.theme_module.ComponentStyles
    
    def test_status_card_style(self):
        """상태 카드 스타일"""
        style = self.ComponentStyles.status_card()
        
        self.assertIn("QFrame", style)
        self.assertIn("border-radius", style)
        self.assertIn(Colors.bg_surface, style)
    
    def test_status_card_custom_color(self):
        """상태 카드 커스텀 색상"""
        custom_color = "#ff0000"
        style = self.ComponentStyles.status_card(title_color=custom_color)
        
        self.assertIn(custom_color, style)
    
    def test_pnl_label_profit(self):
        """PnL 라벨 - 수익"""
        style = self.ComponentStyles.pnl_label(True)
        
        self.assertIn(Colors.success, style)
        self.assertIn("font-weight", style)
    
    def test_pnl_label_loss(self):
        """PnL 라벨 - 손실"""
        style = self.ComponentStyles.pnl_label(False)
        
        self.assertIn(Colors.danger, style)
    
    def test_grade_badge_premium(self):
        """등급 뱃지 - PREMIUM"""
        style = self.ComponentStyles.grade_badge("PREMIUM")
        
        self.assertIn(Colors.grade_premium, style)
        self.assertIn("border-radius", style)


class TestColorConsistency(unittest.TestCase):
    """색상 일관성 테스트 - 기존 테마와 비교"""
    
    def test_bg_base_matches_existing(self):
        """기존 테마의 배경색과 일치"""
        # GUI/styles/theme.py의 BG_DARK = "#0d1117"
        self.assertEqual(Colors.bg_base, "#0d1117")
    
    def test_accent_matches_existing(self):
        """기존 테마의 액센트 색상과 일치"""
        # GUI/styles/theme.py의 ACCENT_PRIMARY = "#00d4aa"
        self.assertEqual(Colors.accent_primary, "#00d4aa")
    
    def test_semantic_colors_match_existing(self):
        """기존 테마의 시맨틱 색상과 일치"""
        # GUI/styles/theme.py의 SUCCESS, DANGER 등
        self.assertEqual(Colors.success, "#3fb950")
        self.assertEqual(Colors.danger, "#f85149")


if __name__ == "__main__":
    print("=" * 60)
    print("TwinStar Quantum - Design System Tests")
    print("=" * 60)
    print(f"Project Root: {PROJECT_ROOT}")
    print(f"Tokens Path: {TOKENS_PATH}")
    print(f"Theme Path: {THEME_PATH}")
    print("=" * 60)
    
    # 테스트 실행
    unittest.main(verbosity=2)
