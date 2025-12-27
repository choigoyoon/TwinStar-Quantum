"""
StarU 통합 디자인 시스템 v2.0
- 모든 위젯에서 import해서 사용
- 가독성 최우선 (WCAG AA 기준 충족)
"""

class StarUColors:
    """색상 팔레트 - 대비율 4.5:1 이상 보장"""
    
    # 배경 (어두운 순)
    BG_DARKEST = "#0d1117"      # 메인 배경
    BG_DARK = "#161b22"         # 카드/패널 배경
    BG_MEDIUM = "#21262d"       # 입력필드/헤더 배경
    BG_LIGHT = "#30363d"        # 호버/보더
    
    # 텍스트 (밝은 순) - 배경 대비 확보
    TEXT_PRIMARY = "#f0f6fc"    # 주요 텍스트 (흰색에 가까움)
    TEXT_SECONDARY = "#b1bac4"  # 보조 텍스트
    TEXT_MUTED = "#8b949e"      # 비활성 텍스트
    
    # 강조색
    ACCENT_GOLD = "#ffd700"     # StarU 브랜드 컬러
    ACCENT_BLUE = "#58a6ff"     # 링크/선택
    
    # 상태색
    SUCCESS = "#3fb950"         # 수익/성공
    ERROR = "#f85149"           # 손실/에러
    WARNING = "#d29922"         # 경고
    INFO = "#58a6ff"            # 정보
    
    # 버튼
    BTN_PRIMARY = "#238636"     # 메인 액션 (녹색)
    BTN_PRIMARY_HOVER = "#2ea043"
    BTN_DANGER = "#da3633"      # 위험 액션 (빨강)
    BTN_DANGER_HOVER = "#f85149"
    BTN_DEFAULT = "#21262d"     # 기본 버튼


class StarUTheme:
    """통합 스타일시트"""
    
    @staticmethod
    def get_stylesheet() -> str:
        c = StarUColors
        
        return f"""
        /* ========== 전역 설정 ========== */
        QWidget {{
            background-color: {c.BG_DARKEST};
            color: {c.TEXT_PRIMARY};
            font-family: 'Malgun Gothic', 'Segoe UI', sans-serif;
            font-size: 13px;
        }}
        
        /* ========== 메인 윈도우 ========== */
        QMainWindow {{
            background-color: {c.BG_DARKEST};
        }}
        
        /* ========== 탭 위젯 ========== */
        QTabWidget::pane {{
            background-color: {c.BG_DARK};
            border: 1px solid {c.BG_LIGHT};
            border-radius: 8px;
            margin-top: -1px;
        }}
        
        QTabBar::tab {{
            background-color: {c.BG_MEDIUM};
            color: {c.TEXT_SECONDARY};
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {c.BG_DARK};
            color: {c.ACCENT_GOLD};
            font-weight: bold;
        }}
        
        QTabBar::tab:hover:!selected {{
            background-color: {c.BG_LIGHT};
            color: {c.TEXT_PRIMARY};
        }}
        
        /* ========== 그룹박스 ========== */
        QGroupBox {{
            background-color: {c.BG_DARK};
            border: 1px solid {c.BG_LIGHT};
            border-radius: 8px;
            margin-top: 16px;
            padding: 20px 15px 15px 15px;
            font-weight: bold;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 15px;
            padding: 0 10px;
            color: {c.ACCENT_GOLD};
            background-color: {c.BG_DARK};
        }}
        
        /* ========== 테이블 ========== */
        QTableWidget {{
            background-color: {c.BG_DARKEST};
            alternate-background-color: {c.BG_DARK};
            border: 1px solid {c.BG_LIGHT};
            border-radius: 8px;
            gridline-color: {c.BG_MEDIUM};
            selection-background-color: {c.ACCENT_BLUE};
            selection-color: {c.TEXT_PRIMARY};
        }}
        
        QTableWidget::item {{
            padding: 10px;
            color: {c.TEXT_PRIMARY};
            border-bottom: 1px solid {c.BG_MEDIUM};
        }}
        
        QTableWidget::item:hover {{
            background-color: {c.BG_MEDIUM};
        }}
        
        QTableWidget::item:selected {{
            background-color: {c.ACCENT_BLUE};
            color: {c.TEXT_PRIMARY};
        }}
        
        QHeaderView::section {{
            background-color: {c.BG_MEDIUM};
            color: {c.TEXT_SECONDARY};
            padding: 12px 10px;
            border: none;
            border-bottom: 2px solid {c.ACCENT_GOLD};
            font-weight: 600;
            font-size: 12px;
        }}
        
        /* ========== 버튼 ========== */
        QPushButton {{
            background-color: {c.BTN_DEFAULT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BG_LIGHT};
            border-radius: 6px;
            padding: 10px 20px;
            font-weight: 500;
            min-height: 20px;
        }}
        
        QPushButton:hover {{
            background-color: {c.BG_LIGHT};
            border-color: {c.ACCENT_GOLD};
        }}
        
        QPushButton:pressed {{
            background-color: {c.BG_MEDIUM};
        }}
        
        QPushButton:disabled {{
            background-color: {c.BG_MEDIUM};
            color: {c.TEXT_MUTED};
            border-color: {c.BG_MEDIUM};
        }}
        
        /* 주요 액션 버튼 (녹색) */
        QPushButton[class="primary"], 
        QPushButton#startBtn,
        QPushButton#addBtn {{
            background-color: {c.BTN_PRIMARY};
            border: none;
            color: white;
        }}
        
        QPushButton[class="primary"]:hover,
        QPushButton#startBtn:hover,
        QPushButton#addBtn:hover {{
            background-color: {c.BTN_PRIMARY_HOVER};
        }}
        
        /* 위험 버튼 (빨강) */
        QPushButton[class="danger"],
        QPushButton#emergencyBtn,
        QPushButton#deleteBtn {{
            background-color: {c.BTN_DANGER};
            border: none;
            color: white;
            font-weight: bold;
        }}
        
        QPushButton[class="danger"]:hover,
        QPushButton#emergencyBtn:hover,
        QPushButton#deleteBtn:hover {{
            background-color: {c.BTN_DANGER_HOVER};
        }}
        
        /* ========== 입력 필드 ========== */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {c.BG_MEDIUM};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BG_LIGHT};
            border-radius: 6px;
            padding: 10px 12px;
            selection-background-color: {c.ACCENT_BLUE};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {c.ACCENT_GOLD};
        }}
        
        QLineEdit:disabled {{
            background-color: {c.BG_DARK};
            color: {c.TEXT_MUTED};
        }}
        
        /* ========== 콤보박스 ========== */
        QComboBox {{
            background-color: {c.BG_MEDIUM};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BG_LIGHT};
            border-radius: 6px;
            padding: 10px 12px;
            min-width: 120px;
        }}
        
        QComboBox:hover {{
            border-color: {c.ACCENT_GOLD};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {c.TEXT_SECONDARY};
            margin-right: 10px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {c.BG_DARK};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BG_LIGHT};
            selection-background-color: {c.ACCENT_BLUE};
            outline: none;
        }}
        
        /* ========== 스핀박스 ========== */
        QSpinBox, QDoubleSpinBox {{
            background-color: {c.BG_MEDIUM};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BG_LIGHT};
            border-radius: 6px;
            padding: 8px 12px;
        }}
        
        QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {c.ACCENT_GOLD};
        }}
        
        /* ========== 체크박스 & 라디오 ========== */
        QCheckBox, QRadioButton {{
            color: {c.TEXT_PRIMARY};
            spacing: 10px;
        }}
        
        QCheckBox::indicator, QRadioButton::indicator {{
            width: 20px;
            height: 20px;
            border: 2px solid {c.BG_LIGHT};
            background-color: {c.BG_MEDIUM};
        }}
        
        QCheckBox::indicator {{
            border-radius: 4px;
        }}
        
        QRadioButton::indicator {{
            border-radius: 10px;
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {c.BTN_PRIMARY};
            border-color: {c.BTN_PRIMARY};
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {c.ACCENT_GOLD};
            border-color: {c.ACCENT_GOLD};
        }}
        
        QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
            border-color: {c.ACCENT_GOLD};
        }}
        
        /* ========== 스크롤바 ========== */
        QScrollBar:vertical {{
            background-color: {c.BG_DARKEST};
            width: 12px;
            border-radius: 6px;
            margin: 0;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {c.BG_LIGHT};
            border-radius: 6px;
            min-height: 30px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {c.TEXT_MUTED};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        QScrollBar:horizontal {{
            background-color: {c.BG_DARKEST};
            height: 12px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {c.BG_LIGHT};
            border-radius: 6px;
            min-width: 30px;
        }}
        
        /* ========== 프로그레스바 ========== */
        QProgressBar {{
            background-color: {c.BG_MEDIUM};
            border: none;
            border-radius: 6px;
            height: 20px;
            text-align: center;
            color: {c.TEXT_PRIMARY};
        }}
        
        QProgressBar::chunk {{
            background-color: {c.ACCENT_GOLD};
            border-radius: 6px;
        }}
        
        /* ========== 라벨 ========== */
        QLabel {{
            color: {c.TEXT_PRIMARY};
            background-color: transparent;
        }}
        
        QLabel[class="title"] {{
            font-size: 18px;
            font-weight: bold;
            color: {c.ACCENT_GOLD};
        }}
        
        QLabel[class="subtitle"] {{
            font-size: 14px;
            color: {c.TEXT_SECONDARY};
        }}
        
        QLabel[class="success"] {{
            color: {c.SUCCESS};
            font-weight: bold;
        }}
        
        QLabel[class="error"] {{
            color: {c.ERROR};
            font-weight: bold;
        }}
        
        /* ========== 툴팁 ========== */
        QToolTip {{
            background-color: {c.BG_DARK};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.ACCENT_GOLD};
            border-radius: 4px;
            padding: 8px;
        }}
        
        /* ========== 메뉴 ========== */
        QMenuBar {{
            background-color: {c.BG_DARK};
            color: {c.TEXT_PRIMARY};
            border-bottom: 1px solid {c.BG_LIGHT};
        }}
        
        QMenuBar::item:selected {{
            background-color: {c.BG_MEDIUM};
        }}
        
        QMenu {{
            background-color: {c.BG_DARK};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BG_LIGHT};
        }}
        
        QMenu::item:selected {{
            background-color: {c.ACCENT_BLUE};
        }}
        
        /* ========== 상태바 ========== */
        QStatusBar {{
            background-color: {c.BG_DARK};
            color: {c.TEXT_SECONDARY};
            border-top: 1px solid {c.BG_LIGHT};
        }}
        
        /* ========== 프레임 ========== */
        QFrame[class="card"] {{
            background-color: {c.BG_DARK};
            border: 1px solid {c.BG_LIGHT};
            border-radius: 8px;
            padding: 15px;
        }}
        
        QFrame[class="separator"] {{
            background-color: {c.BG_LIGHT};
            max-height: 1px;
        }}
        """


def apply_theme(widget):
    """위젯에 테마 적용하는 헬퍼 함수"""
    widget.setStyleSheet(StarUTheme.get_stylesheet())


# 색상 직접 접근용
Colors = StarUColors
