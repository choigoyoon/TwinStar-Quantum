"""
생동감 + 고가독성 프리미엄 테마 (v4.5)
가독성 문제를 해결하기 위해 명도 대비를 극대화하고 투명도를 줄였습니다.

[DEPRECATED] 이 모듈은 ui.design_system.theme으로 대체되었습니다.

마이그레이션:
    # Before
    from GUI.styles.vivid_theme import VividTheme
    
    # After
    from ui.design_system import ThemeGenerator
"""

import warnings


class VividTheme:
    """
    [DEPRECATED] 생동감 + 고가독성 테마
    
    ui.design_system.ThemeGenerator를 사용하세요.
    """
    
    @classmethod
    def get_stylesheet(cls) -> str:
        return """
        /* === 전역 설정 === */
        * {
            font-family: 'Pretendard', 'Malgun Gothic', 'Segoe UI', sans-serif;
            outline: none;
        }
        
        /* === 메인 윈도우 (짙은 배경) === */
        QMainWindow, QWidget#central {
            background-color: #0d1117;  /* 완전한 다크 모드 */
        }
        
        /* === 상태 카드 (선명하게) === */
        QFrame#statusCard {
            background-color: #161b22;  /* 불투명 카드 배경 */
            border: 1px solid #30363d;
            border-radius: 12px;
        }
        
        QFrame#statusCard:hover {
            border: 1px solid #00d4aa;  /* 호버 시 명확한 테두리 */
            background-color: #1c2128;
        }
        
        /* === 그룹박스 (명확한 구분) === */
        QGroupBox {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 12px;
            margin-top: 24px;   /* 타이틀 공간 확보 */
            padding: 20px;
            font-weight: 700;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 16px;
            padding: 4px 12px;
            color: #00d4aa;     /* 민트색 타이틀 */
            font-size: 15px;
            font-weight: bold;
            background-color: #0d1117; /* 타이틀 배경을 어둡게 처리하여 가독성 UP */
            border: 1px solid #30363d;
            border-radius: 6px;
        }
        
        /* === 라벨 텍스트 (고대비) === */
        QLabel {
            color: #e6edf3;     /* 기본 텍스트 밝은 회색 */
            font-weight: 500;
        }
        
        QLabel#valueLabel {
            color: #ffffff;     /* 중요 숫자 완전 흰색 */
            font-size: 26px;
            font-weight: 800;
        }
        
        QLabel#titleLabel {
            color: #8b949e;     /* 보조 텍스트 */
            font-size: 13px;
            font-weight: 600;
        }
        
        /* === 버튼 (가독성 중심) === */
        QPushButton#startBtn {
            background-color: #00d4aa;
            color: #000000;     /* 민트 배경엔 검은 글씨 */
            border-radius: 8px;
            font-weight: 800;
            font-size: 15px;
            padding: 12px;
        }
        
        QPushButton#startBtn:hover {
            background-color: #00ffcc;
        }
        
        QPushButton#stopBtn {
            background-color: #f85149;
            color: #ffffff;     /* 빨강 배경엔 흰 글씨 */
            border-radius: 8px;
            font-weight: 800;
            font-size: 15px;
            padding: 12px;
        }
        
        QPushButton#stopBtn:hover {
            background-color: #ff6b6b;
        }
        
        /* === 입력 필드 (선명함) === */
        QLineEdit, QSpinBox, QDoubleSpinBox {
            background-color: #0d1117;  /* 입력창은 더 어둡게 */
            color: #ffffff;             /* 글씨는 완전 흰색 */
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 10px;
            font-size: 14px;
            font-weight: 600;
        }
        
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
            border: 2px solid #00d4aa;  /* 포커스 강력하게 */
            background-color: #000000;
        }
        
        /* === 콤보박스 === */
        QComboBox {
            background-color: #0d1117;
            color: #ffffff;
            border: 1px solid #30363d;
            border-radius: 6px;
            padding: 10px;
            font-size: 14px;
            font-weight: 600;
        }
        
        QComboBox:hover {
            border: 1px solid #8b949e;
        }
        
        QComboBox QAbstractItemView {
            background-color: #161b22;
            color: #ffffff;
            border: 1px solid #30363d;
            selection-background-color: #1f6feb;
        }
        
        /* === 탭 (명확한 선택) === */
        QTabWidget::pane {
            border: 1px solid #30363d;
            background-color: #161b22;
            border-radius: 8px;
        }
        
        QTabBar::tab {
            background-color: #0d1117;
            color: #8b949e;
            padding: 12px 24px;
            margin-right: 4px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            font-weight: 600;
        }
        
        QTabBar::tab:selected {
            background-color: #161b22;  /* 활성 탭 */
            color: #00d4aa;             /* 활성 텍스트 민트 */
            border-bottom: 3px solid #00d4aa;
        }
        
        /* === 로그창 (콘솔 느낌) === */
        QTextEdit {
            background-color: #000000;  /* 완전 블랙 */
            color: #00ff00;             /* 터미널 그린 */
            font-family: 'Consolas', monospace;
            border: 1px solid #30363d;
            border-radius: 8px;
            font-size: 13px;
        }
        
        /* === 스크롤바 === */
        QScrollBar:vertical {
            background: #0d1117;
            width: 10px;
        }
        QScrollBar::handle:vertical {
            background: #30363d;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background: #8b949e;
        }
        """
