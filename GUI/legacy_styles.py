"""
TwinStar Quantum - TradingView 스타일 테마

[DEPRECATED] 이 모듈은 ui.design_system으로 대체되었습니다.

마이그레이션:
    # Before
    from GUI.legacy_styles import COLORS, MAIN_STYLE, apply_style
    
    # After
    from ui.design_system import Colors, ThemeGenerator
    
    # 색상 접근
    bg = Colors.bg_base  # 대신 COLORS['bg_main'] 사용하던 것
    
    # 스타일 적용
    app.setStyleSheet(ThemeGenerator.generate())

참고: TradingView 스타일의 파란색(#2962ff)은 
새 디자인 시스템의 민트색(#00d4aa)으로 통합되었습니다.
"""

import warnings


def _deprecation_warning():
    warnings.warn(
        "GUI.legacy_styles is deprecated. Use ui.design_system instead.",
        DeprecationWarning,
        stacklevel=3
    )


# [DEPRECATED] TradingView 색상 팔레트
COLORS = {
    # 배경
    'bg_main': '#131722',        # 메인 배경 (TV 다크)
    'bg_card': '#1e222d',        # 카드/패널
    'bg_input': '#2a2e39',       # 입력 필드
    'bg_hover': '#363a45',       # 호버
    
    # 강조
    'primary': '#2962ff',        # 메인 파랑
    'primary_hover': '#1e53e4',  # 파랑 호버
    
    # 수익/손실 (TV 스타일)
    'profit': '#26a69a',         # 수익 청록
    'loss': '#ef5350',           # 손실 산호
    'profit_bg': 'rgba(38, 166, 154, 0.1)',
    'loss_bg': 'rgba(239, 83, 80, 0.1)',
    
    # 텍스트
    'text': '#d1d4dc',           # 메인 텍스트
    'text_dim': '#787b86',       # 흐린 텍스트
    'text_bright': '#ffffff',    # 밝은 텍스트
    
    # 테두리
    'border': '#363a45',         # 기본 테두리
    'border_light': '#434651',   # 밝은 테두리
    
    # 상태
    'warning': '#f7931a',        # 경고 오렌지
    'info': '#2196f3',           # 정보 파랑
}

MAIN_STYLE = f"""
/* ===== 전역 설정 ===== */
* {{
    font-family: -apple-system, BlinkMacSystemFont, 'Trebuchet MS', Roboto, Ubuntu, sans-serif;
}}

QMainWindow, QWidget {{
    background-color: {COLORS['bg_main']};
    color: {COLORS['text']};
    font-size: 12px;
}}

/* ===== 탭 위젯 (TradingView 스타일) ===== */
QTabWidget::pane {{
    border: none;
    background-color: {COLORS['bg_main']};
}}

QTabBar {{
    background-color: {COLORS['bg_main']};
}}

QTabBar::tab {{
    background-color: transparent;
    color: {COLORS['text_dim']};
    border: none;
    border-bottom: 2px solid transparent;
    padding: 12px 24px;
    margin-right: 4px;
    font-size: 13px;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    color: {COLORS['text_bright']};
    border-bottom: 2px solid {COLORS['primary']};
}}

QTabBar::tab:hover:!selected {{
    color: {COLORS['text']};
    background-color: {COLORS['bg_hover']};
}}

/* ===== 버튼 ===== */
QPushButton {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 12px;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {COLORS['bg_hover']};
    border-color: {COLORS['border_light']};
}}

QPushButton:pressed {{
    background-color: {COLORS['primary']};
}}

QPushButton:disabled {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_dim']};
}}

/* 메인 액션 버튼 */
QPushButton[class="primary"], QPushButton#startButton {{
    background-color: {COLORS['primary']};
    color: {COLORS['text_bright']};
    border: none;
    font-weight: 600;
}}

QPushButton[class="primary"]:hover, QPushButton#startButton:hover {{
    background-color: {COLORS['primary_hover']};
}}

/* 수익 버튼 (매수/롱) */
QPushButton[class="buy"], QPushButton#buyButton {{
    background-color: {COLORS['profit']};
    color: {COLORS['text_bright']};
    border: none;
}}

/* 손실 버튼 (매도/숏/중지) */
QPushButton[class="sell"], QPushButton#stopButton, QPushButton#sellButton {{
    background-color: {COLORS['loss']};
    color: {COLORS['text_bright']};
    border: none;
}}

/* ===== 입력 필드 ===== */
QLineEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px 12px;
    selection-background-color: {COLORS['primary']};
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {COLORS['primary']};
}}

/* ===== 콤보박스 ===== */
QComboBox {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px 12px;
    min-width: 100px;
}}

QComboBox:hover {{
    border-color: {COLORS['border_light']};
}}

QComboBox:focus {{
    border-color: {COLORS['primary']};
}}

QComboBox::drop-down {{
    border: none;
    width: 20px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {COLORS['text_dim']};
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['bg_hover']};
    outline: none;
}}

/* ===== 테이블 (TradingView 스타일) ===== */
QTableWidget, QTableView {{
    background-color: {COLORS['bg_main']};
    alternate-background-color: {COLORS['bg_card']};
    border: none;
    gridline-color: {COLORS['border']};
    outline: none;
}}

QTableWidget::item, QTableView::item {{
    padding: 8px;
    border-bottom: 1px solid {COLORS['border']};
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {COLORS['bg_hover']};
    color: {COLORS['text_bright']};
}}

QHeaderView::section {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_dim']};
    padding: 10px 8px;
    border: none;
    border-bottom: 1px solid {COLORS['border']};
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
}}

/* ===== 스크롤바 (미니멀) ===== */
QScrollBar:vertical {{
    background-color: transparent;
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 4px;
    min-height: 40px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['border_light']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    height: 8px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['border']};
    border-radius: 4px;
    min-width: 40px;
}}

/* ===== 그룹박스 ===== */
QGroupBox {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
    margin-top: 12px;
    padding: 12px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: {COLORS['text']};
}}

/* ===== 라벨 ===== */
QLabel {{
    color: {COLORS['text']};
}}

QLabel[class="profit"] {{
    color: {COLORS['profit']};
    font-weight: 600;
}}

QLabel[class="loss"] {{
    color: {COLORS['loss']};
    font-weight: 600;
}}

QLabel[class="title"] {{
    color: {COLORS['text_bright']};
    font-size: 16px;
    font-weight: 600;
}}

QLabel[class="dim"] {{
    color: {COLORS['text_dim']};
}}

/* ===== 체크박스 ===== */
QCheckBox {{
    color: {COLORS['text']};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 1px solid {COLORS['border']};
    background-color: {COLORS['bg_input']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
}}

QCheckBox::indicator:hover {{
    border-color: {COLORS['primary']};
}}

/* ===== 프로그레스바 ===== */
QProgressBar {{
    background-color: {COLORS['bg_input']};
    border: none;
    border-radius: 3px;
    height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {COLORS['primary']};
    border-radius: 3px;
}}

/* ===== 툴팁 ===== */
QToolTip {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 6px 10px;
}}

/* ===== 메뉴바 ===== */
QMenuBar {{
    background-color: {COLORS['bg_main']};
    color: {COLORS['text']};
    border-bottom: 1px solid {COLORS['border']};
}}

QMenuBar::item {{
    padding: 8px 12px;
}}

QMenuBar::item:selected {{
    background-color: {COLORS['bg_hover']};
}}

QMenu {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {COLORS['bg_hover']};
}}

/* ===== 상태바 ===== */
QStatusBar {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_dim']};
    border-top: 1px solid {COLORS['border']};
}}

/* ===== 스플리터 ===== */
QSplitter::handle {{
    background-color: {COLORS['border']};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

/* ===== 프레임 ===== */
QFrame[class="card"] {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border']};
    border-radius: 6px;
}}

QFrame[class="profit-card"] {{
    background-color: {COLORS['profit_bg']};
    border: 1px solid {COLORS['profit']};
    border-radius: 6px;
}}

QFrame[class="loss-card"] {{
    background-color: {COLORS['loss_bg']};
    border: 1px solid {COLORS['loss']};
    border-radius: 6px;
}}

/* ===== 텍스트에딧 ===== */
QTextEdit, QPlainTextEdit {{
    background-color: {COLORS['bg_input']};
    color: {COLORS['text']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 8px;
}}

/* ===== 라디오버튼 ===== */
QRadioButton {{
    color: {COLORS['text']};
    spacing: 8px;
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 8px;
    border: 1px solid {COLORS['border']};
    background-color: {COLORS['bg_input']};
}}

QRadioButton::indicator:checked {{
    background-color: {COLORS['primary']};
    border-color: {COLORS['primary']};
}}
"""


def apply_style(app):
    """
    [DEPRECATED] 앱에 스타일 적용
    
    대신 사용:
        from ui.design_system import ThemeGenerator
        app.setStyleSheet(ThemeGenerator.generate())
    """
    _deprecation_warning()
    app.setStyleSheet(MAIN_STYLE)
    return True


def get_style():
    """
    [DEPRECATED] 스타일시트 반환
    
    대신 사용:
        from ui.design_system import ThemeGenerator
        ThemeGenerator.generate()
    """
    _deprecation_warning()
    return MAIN_STYLE


def get_colors():
    """
    [DEPRECATED] 색상 딕셔너리 반환
    
    대신 사용:
        from ui.design_system import Colors
        Colors.bg_base, Colors.accent_primary, etc.
    """
    _deprecation_warning()
    return COLORS
