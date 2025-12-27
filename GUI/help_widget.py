# help_widget.py - GUI 내장 도움말 (한글 최적화)

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTabWidget, QTextBrowser, QGroupBox,
    QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class HelpWidget(QWidget):
    """기능 설명 위젯 - 한글 폰트 최적화"""
    
    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QLabel, QPushButton, QGroupBox, QTextBrowser {
                font-family: 'Malgun Gothic', '맑은 고딕', sans-serif;
            }
        """)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)
        
        # 헤더
        header = QLabel("📖 기능 설명서")
        header.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
            font-family: 'Malgun Gothic';
        """)
        layout.addWidget(header)
        
        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea { border: none; background: transparent; }
            QScrollBar:vertical { width: 8px; background: #1e2330; }
            QScrollBar::handle:vertical { background: #3a3f4b; border-radius: 4px; }
        """)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(25)
        content_layout.setContentsMargins(0, 0, 20, 0)
        
        # ========== 빠른 시작 ==========
        content_layout.addWidget(self._create_section_header("🚀 빠른 시작 가이드"))
        
        steps = [
            ("1", "데이터 다운로드", "DATA 탭에서 원하는 심볼 선택 후 다운로드"),
            ("2", "파라미터 최적화", "DEV 탭에서 Auto Optimize 실행"),
            ("3", "백테스트", "TEST 탭에서 전략 검증"),
            ("4", "결과 확인", "수익률, 승률, MDD 분석"),
            ("5", "실매매 시작", "TRADE 탭에서 API 연결 후 시작"),
        ]
        
        for num, title, desc in steps:
            content_layout.addWidget(self._create_step_card(num, title, desc))
        
        # ========== 탭 설명 ==========
        content_layout.addWidget(self._create_section_header("📑 각 탭 기능"))
        
        tabs_info = [
            ("🏠 HOME", "대시보드 - 잔고, 시스템 상태, 마켓 티커"),
            ("📊 CHART", "차트 - 캔들차트, 나우캐스트, WebSocket"),
            ("📈 TEST", "백테스트 - 전략 테스트, 결과 분석"),
            ("🎮 TRADE", "실매매 - API 연결, 자동매매"),
            ("📜 LOG", "거래기록 - 히스토리, 통계"),
            ("📥 DATA", "데이터 - 다운로드, 캐시 관리"),
            ("🔧 DEV", "개발자 - 파라미터 최적화"),
            ("⚙️ SET", "설정 - API 키, 알림"),
        ]
        
        for icon_title, desc in tabs_info:
            content_layout.addWidget(self._create_info_row(icon_title, desc))
        
        # ========== 주의사항 ==========
        content_layout.addWidget(self._create_section_header("⚠️ 주의사항"))
        
        warnings = [
            "반드시 Testnet에서 먼저 테스트하세요!",
            "투자 금액은 잃어도 되는 금액만!",
            "API 키 권한은 최소한으로 (출금 비활성화)",
            "24시간 봇 운영 시 서버 사용 권장",
        ]
        
        for w in warnings:
            content_layout.addWidget(self._create_warning_item(w))
        
        # ========== 명령어 ==========
        content_layout.addWidget(self._create_section_header("💻 터미널 명령어"))
        
        commands = [
            ("py GUI/main.py", "GUI 실행"),
            ("py bot_master.py", "마스터 봇 실행"),
            ("py test_integration.py", "통합 테스트"),
        ]
        
        for cmd, desc in commands:
            content_layout.addWidget(self._create_command_row(cmd, desc))
        
        # ========== FAQ ==========
        content_layout.addWidget(self._create_section_header("❓ 자주 묻는 질문"))
        
        faqs = [
            ("GUI가 안 열려요", "test_integration.py로 문제 확인"),
            ("데이터가 없어요", "DATA 탭에서 다운로드"),
            ("API 에러", "API 키 확인, IP 허용 리스트 체크"),
            ("봇이 거래 안 해요", "조건에 맞는 신호가 없을 수 있음"),
        ]
        
        for q, a in faqs:
            content_layout.addWidget(self._create_faq_item(q, a))
        
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _create_section_header(self, text):
        """섹션 헤더"""
        label = QLabel(text)
        label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #58a6ff;
            padding: 15px 0 5px 0;
            border-bottom: 1px solid #2a2e3b;
            font-family: 'Malgun Gothic';
        """)
        return label
    
    def _create_step_card(self, num, title, desc):
        """단계 카드"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: #1e2330;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)
        
        # 번호
        num_label = QLabel(num)
        num_label.setStyleSheet("""
            background: #2962FF;
            color: white;
            font-size: 18px;
            font-weight: bold;
            padding: 10px 15px;
            border-radius: 20px;
            min-width: 20px;
            text-align: center;
        """)
        num_label.setFixedSize(45, 45)
        num_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(num_label)
        
        # 텍스트
        text_layout = QVBoxLayout()
        text_layout.setSpacing(5)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: white; font-size: 16px; font-weight: bold; font-family: 'Malgun Gothic';")
        text_layout.addWidget(title_lbl)
        
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #787b86; font-size: 13px; font-family: 'Malgun Gothic';")
        desc_lbl.setWordWrap(True)
        text_layout.addWidget(desc_lbl)
        
        layout.addLayout(text_layout)
        layout.addStretch()
        
        return frame
    
    def _create_info_row(self, title, desc):
        """정보 행"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: #131722;
                border: 1px solid #2a2e3b;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 8, 15, 8)
        
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("color: white; font-size: 14px; font-weight: bold; min-width: 100px; font-family: 'Malgun Gothic';")
        layout.addWidget(title_lbl)
        
        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet("color: #787b86; font-size: 13px; font-family: 'Malgun Gothic';")
        layout.addWidget(desc_lbl)
        layout.addStretch()
        
        return frame
    
    def _create_warning_item(self, text):
        """경고 항목"""
        label = QLabel(f"  ❗ {text}")
        label.setStyleSheet("""
            color: #ff8a80;
            font-size: 14px;
            padding: 8px 15px;
            background: #2d1a1a;
            border-left: 3px solid #ef5350;
            border-radius: 5px;
            font-family: 'Malgun Gothic';
        """)
        return label
    
    def _create_command_row(self, cmd, desc):
        """명령어 행"""
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: transparent; }")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 5, 0, 5)
        
        cmd_lbl = QLabel(cmd)
        cmd_lbl.setStyleSheet("""
            background: #0d1117;
            color: #58a6ff;
            font-family: Consolas, monospace;
            font-size: 13px;
            padding: 8px 15px;
            border-radius: 5px;
        """)
        layout.addWidget(cmd_lbl)
        
        desc_lbl = QLabel(f"  →  {desc}")
        desc_lbl.setStyleSheet("color: #787b86; font-size: 13px; font-family: 'Malgun Gothic';")
        layout.addWidget(desc_lbl)
        layout.addStretch()
        
        return frame
    
    def _create_faq_item(self, question, answer):
        """FAQ 항목"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: #1e2330;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(5)
        
        q_lbl = QLabel(f"Q: {question}")
        q_lbl.setStyleSheet("color: #58a6ff; font-size: 14px; font-weight: bold; font-family: 'Malgun Gothic';")
        layout.addWidget(q_lbl)
        
        a_lbl = QLabel(f"A: {answer}")
        a_lbl.setStyleSheet("color: #d1d4dc; font-size: 13px; padding-left: 20px; font-family: 'Malgun Gothic';")
        a_lbl.setWordWrap(True)
        layout.addWidget(a_lbl)
        
        return frame


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    w = HelpWidget()
    w.setStyleSheet("background: #0b0e14;")
    w.resize(900, 700)
    w.show()
    sys.exit(app.exec_())
