"""
TwinStar Quantum Theme Generator
================================

통합 테마 생성기 - 모든 Qt 스타일시트를 중앙에서 관리

기존 테마 파일들을 대체:
- GUI/styles/theme.py (Theme)
- GUI/styles/premium_theme.py (PremiumTheme)
- GUI/styles/elegant_theme.py (ElegantTheme)
- GUI/styles/vivid_theme.py (VividTheme)
- GUI/legacy_styles.py

사용법:
    from ui.design_system import ThemeGenerator
    
    # 앱에 테마 적용
    app.setStyleSheet(ThemeGenerator.generate())
    
    # 특정 컴포넌트 스타일만 가져오기
    button_style = ThemeGenerator.get_button_styles()
"""

# 상대 import와 절대 import 모두 지원
try:
    from .tokens import (
        Colors,
        Typography,
        Spacing,
        Radius,
        Shadow,
        get_gradient,
        get_grade_color,
    )
except ImportError:
    # 직접 실행 또는 테스트 환경
    from ui.design_system.tokens import (
        Colors,
        Typography,
        Spacing,
        Radius,
        Shadow,
        get_gradient,
        get_grade_color,
    )


class ThemeGenerator:
    """
    통합 테마 스타일시트 생성기
    
    모든 Qt 위젯의 스타일을 토큰 기반으로 생성
    """
    
    @classmethod
    def generate(cls) -> str:
        """
        전체 스타일시트 생성
        
        Returns:
            Qt 스타일시트 문자열
        """
        return "\n".join([
            cls._get_global_styles(),
            cls._get_main_window_styles(),
            cls._get_button_styles(),
            cls._get_input_styles(),
            cls._get_combobox_styles(),
            cls._get_tab_styles(),
            cls._get_table_styles(),
            cls._get_scrollbar_styles(),
            cls._get_label_styles(),
            cls._get_groupbox_styles(),
            cls._get_textedit_styles(),
            cls._get_checkbox_styles(),
            cls._get_progressbar_styles(),
            cls._get_slider_styles(),
            cls._get_splitter_styles(),
            cls._get_tooltip_styles(),
            cls._get_menu_styles(),
            cls._get_statusbar_styles(),
            cls._get_frame_styles(),
        ])
    
    # ========================================
    # GLOBAL STYLES
    # ========================================
    
    @classmethod
    def _get_global_styles(cls) -> str:
        """전역 스타일"""
        return f"""
        /* ===== Global Styles ===== */
        * {{
            outline: none;
        }}
        
        QWidget {{
            background-color: {Colors.bg_base};
            color: {Colors.text_primary};
            font-family: {Typography.font_sans};
            font-size: {Typography.text_base};
        }}
        """
    
    # ========================================
    # MAIN WINDOW
    # ========================================
    
    @classmethod
    def _get_main_window_styles(cls) -> str:
        """메인 윈도우 스타일"""
        return f"""
        /* ===== Main Window ===== */
        QMainWindow {{
            background-color: {Colors.bg_base};
        }}
        
        QMainWindow::separator {{
            background: {Colors.border_default};
            width: 1px;
            height: 1px;
        }}
        """
    
    # ========================================
    # BUTTONS
    # ========================================
    
    @classmethod
    def _get_button_styles(cls) -> str:
        """버튼 스타일"""
        return f"""
        /* ===== Buttons ===== */
        QPushButton {{
            background: {get_gradient()};
            color: {Colors.text_inverse};
            border: none;
            border-radius: {Radius.radius_sm};
            padding: {Spacing.space_3} {Spacing.space_5};
            font-weight: {Typography.font_semibold};
            font-size: {Typography.text_base};
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
        
        /* Danger Button */
        QPushButton[variant="danger"],
        QPushButton#stopBtn,
        QPushButton#stopButton {{
            background: {Colors.danger};
            color: white;
        }}
        
        QPushButton[variant="danger"]:hover,
        QPushButton#stopBtn:hover,
        QPushButton#stopButton:hover {{
            background: #ff6b6b;
        }}
        
        /* Secondary Button */
        QPushButton[variant="secondary"] {{
            background: {Colors.bg_elevated};
            color: {Colors.text_primary};
            border: 1px solid {Colors.border_default};
        }}
        
        QPushButton[variant="secondary"]:hover {{
            background: {Colors.bg_overlay};
            border-color: {Colors.border_accent};
        }}
        
        /* Ghost Button */
        QPushButton[variant="ghost"] {{
            background: transparent;
            color: {Colors.text_primary};
            border: none;
        }}
        
        QPushButton[variant="ghost"]:hover {{
            background: {Colors.bg_overlay};
        }}
        
        /* Start Button (특수) */
        QPushButton#startBtn,
        QPushButton#startButton {{
            background: {get_gradient()};
            color: {Colors.text_inverse};
            font-weight: {Typography.font_bold};
        }}
        
        QPushButton#startBtn:hover,
        QPushButton#startButton:hover {{
            background: {Colors.accent_hover};
        }}
        
        /* Success Button */
        QPushButton[variant="success"],
        QPushButton#buyButton {{
            background: {Colors.success};
            color: white;
        }}
        """
    
    # ========================================
    # INPUT FIELDS
    # ========================================
    
    @classmethod
    def _get_input_styles(cls) -> str:
        """입력 필드 스타일"""
        return f"""
        /* ===== Input Fields ===== */
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
        
        /* SpinBox Buttons */
        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {{
            background: {Colors.bg_overlay};
            border: none;
            width: 20px;
        }}
        
        QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
        QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{
            background: {Colors.accent_primary};
        }}
        """
    
    # ========================================
    # COMBOBOX
    # ========================================
    
    @classmethod
    def _get_combobox_styles(cls) -> str:
        """콤보박스 스타일"""
        return f"""
        /* ===== ComboBox ===== */
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
    
    # ========================================
    # TABS
    # ========================================
    
    @classmethod
    def _get_tab_styles(cls) -> str:
        """탭 스타일"""
        return f"""
        /* ===== Tabs ===== */
        QTabWidget {{
            background: transparent;
        }}
        
        QTabWidget::pane {{
            border: none;
            background: {Colors.bg_base};
        }}
        
        QTabBar {{
            background: transparent;
        }}
        
        QTabBar::tab {{
            background: transparent;
            color: {Colors.text_secondary};
            padding: {Spacing.space_3} {Spacing.space_6};
            margin-right: {Spacing.space_1};
            border: none;
            border-bottom: 2px solid transparent;
            font-weight: {Typography.font_medium};
            font-size: {Typography.text_base};
        }}
        
        QTabBar::tab:selected {{
            color: {Colors.accent_primary};
            border-bottom: 2px solid {Colors.accent_primary};
            font-weight: {Typography.font_semibold};
        }}
        
        QTabBar::tab:hover:!selected {{
            color: {Colors.text_primary};
            background: {Colors.bg_overlay};
        }}
        
        QTabBar::tab:disabled {{
            color: {Colors.text_muted};
        }}
        """
    
    # ========================================
    # TABLES
    # ========================================
    
    @classmethod
    def _get_table_styles(cls) -> str:
        """테이블 스타일"""
        return f"""
        /* ===== Tables ===== */
        QTableWidget, QTableView {{
            background-color: {Colors.bg_surface};
            alternate-background-color: {Colors.bg_base};
            border: none;
            gridline-color: {Colors.border_muted};
            outline: none;
            font-size: {Typography.text_sm};
        }}
        
        QTableWidget::item, QTableView::item {{
            padding: {Spacing.space_2};
            border-bottom: 1px solid {Colors.border_muted};
        }}
        
        QTableWidget::item:selected, QTableView::item:selected {{
            background-color: {Colors.accent_primary};
            color: {Colors.text_inverse};
        }}
        
        QTableWidget::item:hover, QTableView::item:hover {{
            background-color: {Colors.bg_overlay};
        }}
        
        QHeaderView {{
            background-color: {Colors.bg_surface};
        }}
        
        QHeaderView::section {{
            background-color: {Colors.bg_elevated};
            color: {Colors.text_secondary};
            padding: {Spacing.space_3} {Spacing.space_2};
            border: none;
            border-bottom: 1px solid {Colors.border_default};
            font-weight: {Typography.font_semibold};
            font-size: {Typography.text_sm};
            text-transform: uppercase;
        }}
        
        QHeaderView::section:hover {{
            background-color: {Colors.bg_overlay};
        }}
        """
    
    # ========================================
    # SCROLLBAR
    # ========================================
    
    @classmethod
    def _get_scrollbar_styles(cls) -> str:
        """스크롤바 스타일"""
        return f"""
        /* ===== Scrollbar ===== */
        QScrollBar:vertical {{
            background: transparent;
            width: 10px;
            margin: 0;
        }}
        
        QScrollBar::handle:vertical {{
            background: {Colors.border_default};
            border-radius: 5px;
            min-height: 40px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {Colors.accent_primary};
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
        
        /* Horizontal */
        QScrollBar:horizontal {{
            background: transparent;
            height: 10px;
            margin: 0;
        }}
        
        QScrollBar::handle:horizontal {{
            background: {Colors.border_default};
            border-radius: 5px;
            min-width: 40px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background: {Colors.accent_primary};
        }}
        
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        """
    
    # ========================================
    # LABELS
    # ========================================
    
    @classmethod
    def _get_label_styles(cls) -> str:
        """라벨 스타일"""
        return f"""
        /* ===== Labels ===== */
        QLabel {{
            color: {Colors.text_primary};
            background: transparent;
        }}
        
        QLabel[variant="muted"],
        QLabel#titleLabel {{
            color: {Colors.text_secondary};
            font-size: {Typography.text_sm};
        }}
        
        QLabel[variant="success"] {{
            color: {Colors.success};
            font-weight: {Typography.font_semibold};
        }}
        
        QLabel[variant="danger"] {{
            color: {Colors.danger};
            font-weight: {Typography.font_semibold};
        }}
        
        QLabel[variant="warning"] {{
            color: {Colors.warning};
            font-weight: {Typography.font_semibold};
        }}
        
        QLabel[variant="accent"] {{
            color: {Colors.accent_primary};
            font-weight: {Typography.font_semibold};
        }}
        
        QLabel#valueLabel {{
            color: {Colors.text_primary};
            font-size: {Typography.text_3xl};
            font-weight: {Typography.font_bold};
        }}
        
        QLabel[variant="title"] {{
            color: {Colors.text_primary};
            font-size: {Typography.text_xl};
            font-weight: {Typography.font_semibold};
        }}
        """
    
    # ========================================
    # GROUPBOX
    # ========================================
    
    @classmethod
    def _get_groupbox_styles(cls) -> str:
        """그룹박스 스타일"""
        return f"""
        /* ===== GroupBox ===== */
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
    
    # ========================================
    # TEXTEDIT (LOG)
    # ========================================
    
    @classmethod
    def _get_textedit_styles(cls) -> str:
        """텍스트 편집기 스타일 (로그창)"""
        return f"""
        /* ===== TextEdit / Log ===== */
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
        
        QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {Colors.border_accent};
        }}
        """
    
    # ========================================
    # CHECKBOX
    # ========================================
    
    @classmethod
    def _get_checkbox_styles(cls) -> str:
        """체크박스 스타일"""
        return f"""
        /* ===== CheckBox ===== */
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
        
        /* Radio Button */
        QRadioButton {{
            color: {Colors.text_primary};
            spacing: {Spacing.space_2};
        }}
        
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 9px;
            border: 2px solid {Colors.border_default};
            background: {Colors.bg_elevated};
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {Colors.accent_primary};
            border-color: {Colors.accent_primary};
        }}
        """
    
    # ========================================
    # PROGRESSBAR
    # ========================================
    
    @classmethod
    def _get_progressbar_styles(cls) -> str:
        """프로그레스바 스타일"""
        return f"""
        /* ===== ProgressBar ===== */
        QProgressBar {{
            background-color: {Colors.bg_elevated};
            border: none;
            border-radius: {Radius.radius_sm};
            height: 8px;
            text-align: center;
            color: {Colors.text_primary};
            font-size: {Typography.text_xs};
        }}
        
        QProgressBar::chunk {{
            background: {get_gradient()};
            border-radius: {Radius.radius_sm};
        }}
        """
    
    # ========================================
    # SLIDER
    # ========================================
    
    @classmethod
    def _get_slider_styles(cls) -> str:
        """슬라이더 스타일"""
        return f"""
        /* ===== Slider ===== */
        QSlider::groove:horizontal {{
            background: {Colors.bg_elevated};
            height: 6px;
            border-radius: 3px;
        }}
        
        QSlider::handle:horizontal {{
            background: {Colors.accent_primary};
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background: {Colors.accent_hover};
        }}
        
        QSlider::sub-page:horizontal {{
            background: {get_gradient()};
            border-radius: 3px;
        }}
        
        /* Vertical Slider */
        QSlider::groove:vertical {{
            background: {Colors.bg_elevated};
            width: 6px;
            border-radius: 3px;
        }}
        
        QSlider::handle:vertical {{
            background: {Colors.accent_primary};
            width: 16px;
            height: 16px;
            margin: 0 -5px;
            border-radius: 8px;
        }}
        """
    
    # ========================================
    # SPLITTER
    # ========================================
    
    @classmethod
    def _get_splitter_styles(cls) -> str:
        """스플리터 스타일"""
        return f"""
        /* ===== Splitter ===== */
        QSplitter::handle {{
            background: {Colors.border_default};
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        QSplitter::handle:hover {{
            background: {Colors.accent_primary};
        }}
        """
    
    # ========================================
    # TOOLTIP
    # ========================================
    
    @classmethod
    def _get_tooltip_styles(cls) -> str:
        """툴팁 스타일"""
        return f"""
        /* ===== ToolTip ===== */
        QToolTip {{
            background-color: {Colors.bg_surface};
            color: {Colors.text_primary};
            border: 1px solid {Colors.border_default};
            border-radius: {Radius.radius_sm};
            padding: {Spacing.space_2} {Spacing.space_3};
            font-size: {Typography.text_sm};
        }}
        """
    
    # ========================================
    # MENU
    # ========================================
    
    @classmethod
    def _get_menu_styles(cls) -> str:
        """메뉴 스타일"""
        return f"""
        /* ===== Menu Bar ===== */
        QMenuBar {{
            background-color: {Colors.bg_base};
            color: {Colors.text_primary};
            border-bottom: 1px solid {Colors.border_default};
            padding: {Spacing.space_1};
        }}
        
        QMenuBar::item {{
            padding: {Spacing.space_2} {Spacing.space_3};
            background: transparent;
            border-radius: {Radius.radius_sm};
        }}
        
        QMenuBar::item:selected {{
            background-color: {Colors.bg_overlay};
        }}
        
        /* Menu */
        QMenu {{
            background-color: {Colors.bg_surface};
            border: 1px solid {Colors.border_default};
            border-radius: {Radius.radius_md};
            padding: {Spacing.space_1};
        }}
        
        QMenu::item {{
            padding: {Spacing.space_2} {Spacing.space_6};
            border-radius: {Radius.radius_sm};
        }}
        
        QMenu::item:selected {{
            background-color: {Colors.bg_overlay};
        }}
        
        QMenu::separator {{
            height: 1px;
            background: {Colors.border_default};
            margin: {Spacing.space_1} {Spacing.space_2};
        }}
        """
    
    # ========================================
    # STATUSBAR
    # ========================================
    
    @classmethod
    def _get_statusbar_styles(cls) -> str:
        """상태바 스타일"""
        return f"""
        /* ===== Status Bar ===== */
        QStatusBar {{
            background-color: {Colors.bg_surface};
            color: {Colors.text_secondary};
            border-top: 1px solid {Colors.border_default};
            font-size: {Typography.text_sm};
        }}
        
        QStatusBar::item {{
            border: none;
        }}
        """
    
    # ========================================
    # FRAME
    # ========================================
    
    @classmethod
    def _get_frame_styles(cls) -> str:
        """프레임 스타일"""
        return f"""
        /* ===== Frame ===== */
        QFrame[variant="card"],
        QFrame#statusCard {{
            background-color: {Colors.bg_surface};
            border: 1px solid {Colors.border_default};
            border-radius: {Radius.radius_lg};
        }}
        
        QFrame[variant="card"]:hover,
        QFrame#statusCard:hover {{
            border-color: {Colors.accent_primary};
        }}
        
        QFrame[variant="success"] {{
            background-color: {Colors.success_bg};
            border: 1px solid {Colors.success};
            border-radius: {Radius.radius_md};
        }}
        
        QFrame[variant="danger"] {{
            background-color: {Colors.danger_bg};
            border: 1px solid {Colors.danger};
            border-radius: {Radius.radius_md};
        }}
        """


# ============================================================
# COMPONENT-SPECIFIC GENERATORS
# ============================================================

class ComponentStyles:
    """
    개별 컴포넌트 스타일 헬퍼
    
    특정 위젯에만 적용할 스타일이 필요할 때 사용
    """
    
    @staticmethod
    def status_card(title_color: str | None = None) -> str:
        """상태 카드 스타일"""
        color = title_color if title_color is not None else Colors.accent_primary
        return f"""
            QFrame {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_lg};
            }}
            QFrame:hover {{
                border-color: {color};
            }}
            QLabel#title {{
                color: {Colors.text_secondary};
                font-size: {Typography.text_sm};
            }}
            QLabel#value {{
                color: {Colors.text_primary};
                font-size: {Typography.text_2xl};
                font-weight: {Typography.font_bold};
            }}
        """
    
    @staticmethod
    def pnl_label(is_profit: bool) -> str:
        """PnL 라벨 스타일"""
        color = Colors.success if is_profit else Colors.danger
        return f"""
            QLabel {{
                color: {color};
                font-weight: {Typography.font_bold};
            }}
        """
    
    @staticmethod
    def grade_badge(grade: str) -> str:
        """등급 뱃지 스타일"""
        color = get_grade_color(grade)
        return f"""
            QLabel {{
                color: {color};
                background-color: {Colors.bg_surface};
                border: 2px solid {color};
                border-radius: {Radius.radius_md};
                padding: {Spacing.space_2} {Spacing.space_4};
                font-size: {Typography.text_xl};
                font-weight: {Typography.font_bold};
            }}
        """
