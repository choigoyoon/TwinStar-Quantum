"""
TwinStar Quantum - 프리미엄 테마 시스템

[DEPRECATED] 이 모듈은 ui.design_system.theme으로 대체되었습니다.

마이그레이션:
    # Before
    from GUI.styles.theme import Theme
    
    # After  
    from ui.design_system import ThemeGenerator, Colors
"""



class Theme:
    """
    [DEPRECATED] 다크 프리미엄 테마
    
    ui.design_system.ThemeGenerator를 사용하세요.
    """
    
    # === 배경색 ===
    BG_DARK = "#0d1117"      # 최상위 배경
    BG_CARD = "#161b22"      # 카드 배경
    BG_INPUT = "#21262d"     # 입력 필드 배경
    BG_HOVER = "#30363d"     # 호버 상태
    
    # === 텍스트 ===
    TEXT_PRIMARY = "#f0f6fc"    # 주요 텍스트
    TEXT_SECONDARY = "#8b949e"  # 보조 텍스트
    TEXT_MUTED = "#484f58"      # 비활성 텍스트
    
    # === 액센트 (네온) ===
    ACCENT_PRIMARY = "#00d4aa"    # 민트 (메인)
    ACCENT_SECONDARY = "#58a6ff"  # 블루
    ACCENT_GRADIENT = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00d4aa, stop:1 #00b894)"
    
    # === 상태색 ===
    SUCCESS = "#3fb950"    # 수익/성공
    DANGER = "#f85149"     # 손실/위험
    WARNING = "#d29922"    # 경고
    INFO = "#58a6ff"       # 정보
    
    # === 크기 ===
    RADIUS_SM = "6px"
    RADIUS_MD = "10px"
    RADIUS_LG = "16px"
    
    FONT_SM = "12px"
    FONT_MD = "14px"
    FONT_LG = "18px"
    FONT_XL = "24px"
    
    # === 그림자 ===
    SHADOW = "0 4px 12px rgba(0, 0, 0, 0.4)"
    
    @classmethod
    def get_stylesheet(cls) -> str:
        return f"""
        /* === 전역 === */
        QWidget {{
            background-color: {cls.BG_DARK};
            color: {cls.TEXT_PRIMARY};
            font-family: 'Pretendard', 'Inter', 'Segoe UI', sans-serif;
            font-size: {cls.FONT_MD};
        }}
        
        /* === 메인 윈도우 === */
        QMainWindow {{
            background-color: {cls.BG_DARK};
        }}
        
        /* === 카드/그룹박스 === */
        QGroupBox {{
            background-color: {cls.BG_CARD};
            border: 1px solid {cls.BG_HOVER};
            border-radius: {cls.RADIUS_MD};
            margin-top: 12px;
            padding: 16px;
            font-weight: 600;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 8px;
            color: {cls.ACCENT_PRIMARY};
        }}
        
        /* === 버튼 === */
        QPushButton {{
            background: {cls.ACCENT_GRADIENT};
            color: {cls.BG_DARK};
            border: none;
            border-radius: {cls.RADIUS_SM};
            padding: 10px 20px;
            font-weight: 600;
            min-height: 36px;
        }}
        
        QPushButton:hover {{
            background: {cls.ACCENT_PRIMARY};
        }}
        
        QPushButton:pressed {{
            background: #00b894;
        }}
        
        QPushButton:disabled {{
            background: {cls.BG_INPUT};
            color: {cls.TEXT_MUTED};
        }}
        
        /* === 위험 버튼 === */
        QPushButton[danger="true"] {{
            background: {cls.DANGER};
            color: white;
        }}
        
        /* === 보조 버튼 === */
        QPushButton[secondary="true"] {{
            background: {cls.BG_INPUT};
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BG_HOVER};
        }}
        
        /* === 입력 필드 === */
        QLineEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {cls.BG_INPUT};
            border: 1px solid {cls.BG_HOVER};
            border-radius: {cls.RADIUS_SM};
            padding: 8px 12px;
            color: {cls.TEXT_PRIMARY};
            min-height: 36px;
        }}
        
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border-color: {cls.ACCENT_PRIMARY};
        }}
        
        /* === 콤보박스 === */
        QComboBox {{
            background-color: {cls.BG_INPUT};
            border: 1px solid {cls.BG_HOVER};
            border-radius: {cls.RADIUS_SM};
            padding: 8px 12px;
            min-height: 36px;
        }}
        
        QComboBox:hover {{
            border-color: {cls.ACCENT_PRIMARY};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {cls.BG_CARD};
            border: 1px solid {cls.BG_HOVER};
            selection-background-color: {cls.ACCENT_PRIMARY};
            selection-color: {cls.BG_DARK};
        }}
        
        /* === 탭 === */
        QTabWidget::pane {{
            border: none;
            background: {cls.BG_DARK};
        }}
        
        QTabBar::tab {{
            background: {cls.BG_CARD};
            color: {cls.TEXT_SECONDARY};
            padding: 12px 24px;
            margin-right: 4px;
            border-top-left-radius: {cls.RADIUS_SM};
            border-top-right-radius: {cls.RADIUS_SM};
        }}
        
        QTabBar::tab:selected {{
            background: {cls.ACCENT_PRIMARY};
            color: {cls.BG_DARK};
            font-weight: 600;
        }}
        
        QTabBar::tab:hover:!selected {{
            background: {cls.BG_HOVER};
        }}
        
        /* === 라벨 === */
        QLabel {{
            color: {cls.TEXT_PRIMARY};
        }}
        
        QLabel[muted="true"] {{
            color: {cls.TEXT_SECONDARY};
            font-size: {cls.FONT_SM};
        }}
        
        QLabel[success="true"] {{
            color: {cls.SUCCESS};
        }}
        
        QLabel[danger="true"] {{
            color: {cls.DANGER};
        }}
        
        QLabel[accent="true"] {{
            color: {cls.ACCENT_PRIMARY};
            font-weight: 600;
        }}
        
        /* === 스크롤바 === */
        QScrollBar:vertical {{
            background: {cls.BG_CARD};
            width: 8px;
            border-radius: 4px;
        }}
        
        QScrollBar::handle:vertical {{
            background: {cls.BG_HOVER};
            border-radius: 4px;
            min-height: 30px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: {cls.ACCENT_PRIMARY};
        }}
        
        /* === 테이블 === */
        QTableWidget {{
            background-color: {cls.BG_CARD};
            border: none;
            gridline-color: {cls.BG_HOVER};
        }}
        
        QTableWidget::item {{
            padding: 8px;
        }}
        
        QTableWidget::item:selected {{
            background-color: {cls.ACCENT_PRIMARY};
            color: {cls.BG_DARK};
        }}
        
        QHeaderView::section {{
            background-color: {cls.BG_INPUT};
            color: {cls.TEXT_SECONDARY};
            padding: 10px;
            border: none;
            font-weight: 600;
        }}
        
        /* === 프로그레스바 === */
        QProgressBar {{
            background-color: {cls.BG_INPUT};
            border: none;
            border-radius: {cls.RADIUS_SM};
            height: 8px;
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background: {cls.ACCENT_GRADIENT};
            border-radius: {cls.RADIUS_SM};
        }}
        
        /* === 로그 영역 === */
        QTextEdit {{
            background-color: {cls.BG_INPUT};
            border: 1px solid {cls.BG_HOVER};
            border-radius: {cls.RADIUS_SM};
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: {cls.FONT_SM};
            padding: 8px;
        }}
        
        /* === 체크박스 === */
        QCheckBox {{
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 2px solid {cls.BG_HOVER};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {cls.ACCENT_PRIMARY};
            border-color: {cls.ACCENT_PRIMARY};
        }}
        
        /* === 슬라이더 === */
        QSlider::groove:horizontal {{
            background: {cls.BG_INPUT};
            height: 6px;
            border-radius: 3px;
        }}
        
        QSlider::handle:horizontal {{
            background: {cls.ACCENT_PRIMARY};
            width: 16px;
            height: 16px;
            margin: -5px 0;
            border-radius: 8px;
        }}
        
        /* === 스플리터 === */
        QSplitter::handle {{
            background: {cls.BG_HOVER};
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        """
