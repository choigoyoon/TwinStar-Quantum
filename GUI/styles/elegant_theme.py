"""
세련된 테마 - 기존 구조에 적용

[DEPRECATED] 이 모듈은 ui.design_system.theme으로 대체되었습니다.

마이그레이션:
    # Before
    from GUI.styles.elegant_theme import ElegantTheme
    
    # After
    from ui.design_system import ThemeGenerator
"""



class ElegantTheme:
    """
    [DEPRECATED] 고급스러운 다크 테마
    
    ui.design_system.ThemeGenerator를 사용하세요.
    """
    
    # === 배경 (그라데이션) ===
    BG_GRADIENT = """
        qlineargradient(
            x1:0, y1:0, x2:0, y2:1,
            stop:0 #1a1d23,
            stop:1 #0f1115
        )
    """
    BG_DARK = "#13161b"
    BG_CARD = "rgba(255, 255, 255, 0.03)"  # 반투명 카드
    BG_INPUT = "rgba(255, 255, 255, 0.05)"
    BG_HOVER = "rgba(255, 255, 255, 0.08)"
    
    # === 테두리 (은은하게) ===
    BORDER_SUBTLE = "rgba(255, 255, 255, 0.06)"
    BORDER_FOCUS = "rgba(0, 212, 170, 0.5)"
    
    # === 텍스트 ===
    TEXT_PRIMARY = "#e8eaed"
    TEXT_SECONDARY = "#9aa0a6"
    TEXT_MUTED = "#5f6368"
    
    # === 액센트 (은은한 민트) ===
    ACCENT = "#00d4aa"
    ACCENT_SOFT = "rgba(0, 212, 170, 0.15)"
    ACCENT_GLOW = "rgba(0, 212, 170, 0.3)"
    
    # === 상태 (부드러운 톤) ===
    SUCCESS = "#34a853"
    SUCCESS_BG = "rgba(52, 168, 83, 0.1)"
    DANGER = "#ea4335"
    DANGER_BG = "rgba(234, 67, 53, 0.1)"
    WARNING = "#fbbc04"
    
    # === 그림자 ===
    SHADOW_SOFT = "0 2px 8px rgba(0, 0, 0, 0.3)"
    SHADOW_MEDIUM = "0 4px 16px rgba(0, 0, 0, 0.4)"
    SHADOW_GLOW = "0 0 20px rgba(0, 212, 170, 0.2)"
    
    @classmethod
    def get_stylesheet(cls) -> str:
        return f"""
        /* === 전역 === */
        QWidget {{
            background-color: {cls.BG_DARK};
            color: {cls.TEXT_PRIMARY};
            font-family: 'Pretendard', 'SF Pro Display', 'Segoe UI', sans-serif;
            font-size: 14px;
        }}
        
        /* === 카드/그룹박스 (부드러운 그림자) === */
        QGroupBox {{
            background-color: {cls.BG_CARD};
            border: 1px solid {cls.BORDER_SUBTLE};
            border-radius: 12px;
            margin-top: 8px;
            padding: 16px;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 8px;
            color: {cls.ACCENT};
            font-weight: 500;
            font-size: 13px;
        }}
        
        /* === 버튼 (글래스모피즘) === */
        QPushButton {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0, 212, 170, 0.9),
                stop:1 rgba(0, 180, 148, 0.9)
            );
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-weight: 500;
            font-size: 14px;
        }}
        
        QPushButton:hover {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(0, 230, 190, 1),
                stop:1 rgba(0, 200, 165, 1)
            );
        }}
        
        QPushButton:pressed {{
            background: rgba(0, 160, 130, 1);
        }}
        
        QPushButton:disabled {{
            background: rgba(255, 255, 255, 0.05);
            color: {cls.TEXT_MUTED};
        }}
        
        /* === 위험 버튼 === */
        QPushButton[class="danger"] {{
            background: qlineargradient(
                x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(234, 67, 53, 0.9),
                stop:1 rgba(200, 50, 40, 0.9)
            );
        }}
        
        /* === 입력 필드 (미니멀) === */
        QLineEdit, QSpinBox, QDoubleSpinBox {{
            background-color: {cls.BG_INPUT};
            border: 1px solid {cls.BORDER_SUBTLE};
            border-radius: 6px;
            padding: 8px 12px;
            color: {cls.TEXT_PRIMARY};
            selection-background-color: {cls.ACCENT_SOFT};
        }}
        
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
            border: 1px solid {cls.BORDER_FOCUS};
            background-color: rgba(255, 255, 255, 0.07);
        }}
        
        /* === 콤보박스 === */
        QComboBox {{
            background-color: {cls.BG_INPUT};
            border: 1px solid {cls.BORDER_SUBTLE};
            border-radius: 6px;
            padding: 8px 12px;
            min-height: 20px;
        }}
        
        QComboBox:hover {{
            background-color: {cls.BG_HOVER};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: #1e2229;
            border: 1px solid {cls.BORDER_SUBTLE};
            border-radius: 6px;
            selection-background-color: {cls.ACCENT_SOFT};
            outline: none;
        }}
        
        /* === 탭 (미니멀) === */
        QTabWidget::pane {{
            border: none;
            background: transparent;
        }}
        
        QTabBar::tab {{
            background: transparent;
            color: {cls.TEXT_SECONDARY};
            padding: 10px 20px;
            margin-right: 4px;
            border-bottom: 2px solid transparent;
        }}
        
        QTabBar::tab:selected {{
            color: {cls.ACCENT};
            border-bottom: 2px solid {cls.ACCENT};
        }}
        
        QTabBar::tab:hover:!selected {{
            color: {cls.TEXT_PRIMARY};
        }}
        
        /* === 라벨 === */
        QLabel {{
            color: {cls.TEXT_PRIMARY};
            background: transparent;
        }}
        
        /* === 스크롤바 (얇고 미니멀) === */
        QScrollBar:vertical {{
            background: transparent;
            width: 6px;
            margin: 4px;
        }}
        
        QScrollBar::handle:vertical {{
            background: rgba(255, 255, 255, 0.15);
            border-radius: 3px;
            min-height: 30px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: rgba(255, 255, 255, 0.25);
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        /* === 테이블 === */
        QTableWidget {{
            background-color: transparent;
            border: none;
            gridline-color: {cls.BORDER_SUBTLE};
        }}
        
        QTableWidget::item {{
            padding: 8px;
            border-bottom: 1px solid {cls.BORDER_SUBTLE};
        }}
        
        QTableWidget::item:selected {{
            background-color: {cls.ACCENT_SOFT};
        }}
        
        QHeaderView::section {{
            background-color: transparent;
            color: {cls.TEXT_SECONDARY};
            padding: 10px;
            border: none;
            border-bottom: 1px solid {cls.BORDER_SUBTLE};
            font-weight: 500;
            font-size: 12px;
        }}
        
        /* === 로그 영역 === */
        QTextEdit {{
            background-color: rgba(0, 0, 0, 0.2);
            border: 1px solid {cls.BORDER_SUBTLE};
            border-radius: 8px;
            font-family: 'JetBrains Mono', 'Consolas', monospace;
            font-size: 12px;
            padding: 8px;
            selection-background-color: {cls.ACCENT_SOFT};
        }}
        
        /* === 체크박스 === */
        QCheckBox {{
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid {cls.BORDER_SUBTLE};
            background: {cls.BG_INPUT};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {cls.ACCENT};
            border-color: {cls.ACCENT};
        }}
        
        /* === 프로그레스바 === */
        QProgressBar {{
            background-color: rgba(255, 255, 255, 0.05);
            border: none;
            border-radius: 4px;
            height: 6px;
            text-align: center;
        }}
        
        QProgressBar::chunk {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {cls.ACCENT},
                stop:1 #00b894
            );
            border-radius: 4px;
        }}
        
        /* === 스플리터 === */
        QSplitter::handle {{
            background: {cls.BORDER_SUBTLE};
            margin: 2px;
        }}
        
        QSplitter::handle:horizontal {{
            width: 1px;
        }}
        
        QSplitter::handle:vertical {{
            height: 1px;
        }}
        
        /* === 툴팁 === */
        QToolTip {{
            background-color: #252a31;
            color: {cls.TEXT_PRIMARY};
            border: 1px solid {cls.BORDER_SUBTLE};
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 12px;
        }}
        """
