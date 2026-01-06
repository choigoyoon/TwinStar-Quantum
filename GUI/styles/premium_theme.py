"""
프리미엄 테마 + 폰트 시스템
"""

from GUI.styles.fonts import FontSystem

class PremiumTheme:
    """폰트 + 스타일 통합 테마"""
    
    @classmethod
    def get_stylesheet(cls) -> str:
        # 사용 가능한 폰트 확인
        main_font = FontSystem.get_best_font()
        mono_font = FontSystem.get_mono_font()
        
        return f"""
        /* === 전역 폰트 강제 적용 === */
        QWidget {{
            font-family: '{main_font}', 'Pretendard', 'Malgun Gothic', sans-serif;
            outline: none;
        }}
        
        /* === 메인 윈도우 === */
        QMainWindow, QWidget#central {{
            background-color: #0d1117;
            color: #f0f6fc;
            font-size: 14px;
            font-family: '{main_font}', sans-serif;
        }}
        
        /* === 제목 (크고 굵게) === */
        QLabel#titleLabel {{
            font-size: 13px;
            font-weight: 600;
            letter-spacing: 0.5px;
            color: #8b949e;
        }}
        
        /* === 숫자 (특별 처리) === */
        QLabel#valueLabel {{
            font-family: 'Inter', '{main_font}', sans-serif;
            font-size: 28px;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
            letter-spacing: -0.5px;
            color: #ffffff;
        }}
        
        /* === 섹션 헤더 === */
        QGroupBox::title {{
            font-size: 15px;
            font-weight: 600;
            letter-spacing: 0.3px;
        }}
        
        /* === 버튼 === */
        QPushButton {{
            font-size: 14px;
            font-weight: 600;
            letter-spacing: 0.3px;
            padding: 12px 24px;
            border-radius: 10px;
        }}
        
        QPushButton#startBtn {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 #00d4aa, stop:1 #00b894
            );
            color: #0d1117;
            border: none;
        }}
        
        QPushButton#startBtn:hover {{
            background: #00e6b8;
        }}
        
        QPushButton#stopBtn {{
            background: #f85149;
            color: white;
            border: none;
        }}
        
        /* === 입력 필드 === */
        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            font-size: 14px;
            font-weight: 500;
            padding: 10px 14px;
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 8px;
            color: #f0f6fc;
        }}
        
        QLineEdit:focus, QSpinBox:focus, 
        QDoubleSpinBox:focus, QComboBox:focus {{
            border: 2px solid #00d4aa;
            background-color: #000000;
        }}
        
        /* === 탭 (폰트 통일) === */
        QTabWidget {{
            font-family: 'Pretendard', 'Spoqa Han Sans', 'Noto Sans KR', '맑은 고딕', sans-serif;
            font-size: 14px;
        }}

        QTabWidget::pane {{
            border: 1px solid #30363d;
            background-color: #161b22;
            border-radius: 8px;
        }}
        
        QTabBar {{
            font-family: 'Pretendard', 'Spoqa Han Sans', 'Noto Sans KR', '맑은 고딕', sans-serif;
            font-size: 14px;
            font-weight: 600;
        }}

        QTabBar::tab {{
            font-family: 'Pretendard', 'Spoqa Han Sans', 'Noto Sans KR', '맑은 고딕', sans-serif;
            font-size: 14px;
            font-weight: 500;
            padding: 10px 20px;
            min-width: 100px;
            color: #9aa0a6;
            background: transparent;
            border: none;
            border-bottom: 2px solid transparent;
        }}
        
        QTabBar::tab:selected {{
            font-weight: 600;
            color: #00d4aa;
            border-bottom: 2px solid #00d4aa;
        }}

        QTabBar::tab:hover:!selected {{
            color: #e6edf3;
            background: rgba(255, 255, 255, 0.05);
        }}
        
        /* === 그룹박스 === */
        QGroupBox {{
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            margin-top: 16px;
            padding: 20px;
        }}
        
        QGroupBox::title {{
            color: #00d4aa;
            subcontrol-origin: margin;
            left: 16px;
            padding: 0 8px;
            background-color: #0d1117;
            border: 1px solid #30363d;
            border-radius: 6px;
        }}
        
        /* === 로그 (모노스페이스) === */
        QTextEdit {{
            font-family: '{mono_font}', monospace;
            font-size: 13px;
            line-height: 1.5;
            background-color: #000000;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 12px;
            color: #00ff00;
        }}
        
        /* === 테이블 === */
        QTableWidget {{
            font-size: 13px;
            background: transparent;
            border: none;
        }}
        
        QTableWidget::item {{
            padding: 10px;
            border-bottom: 1px solid #30363d;
        }}
        
        QHeaderView::section {{
            font-family: '{main_font}', sans-serif;
            font-size: 12px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #8b949e;
            background-color: #161b22;
            padding: 10px;
            border: none;
        }}
        
        /* === 스크롤바 === */
        QScrollBar:vertical {{
            width: 10px;
            background: #0d1117;
        }}
        
        QScrollBar::handle:vertical {{
            background: #30363d;
            border-radius: 4px;
            min-height: 40px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background: #00d4aa;
        }}
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        /* === 체크박스 === */
        QCheckBox {{
            font-size: 14px;
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 2px solid #30363d;
        }}
        
        QCheckBox::indicator:checked {{
            background: #00d4aa;
            border-color: #00d4aa;
        }}
        
        /* === 콤보박스 드롭다운 === */
        QComboBox QAbstractItemView {{
            font-size: 14px;
            background: #1c2128;
            border: 1px solid #30363d;
            border-radius: 8px;
            selection-background-color: rgba(0, 212, 170, 0.2);
            color: #ffffff;
        }}
        
        /* === 상태 카드 === */
        QFrame#statusCard {{
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
        }}
        QFrame#statusCard:hover {{
            border: 1px solid #00d4aa;
        }}
        """
