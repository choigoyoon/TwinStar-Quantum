"""
온보딩 튜토리얼 다이얼로그
- 첫 실행 시 표시
- 단계별 가이드
"""

import sys
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QStackedWidget, QWidget, QFrame
)
from PyQt5.QtCore import Qt


class OnboardingDialog(QDialog):
    """온보딩 튜토리얼"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_step = 0
        self._init_ui()
    
    def _init_ui(self):
        self.setWindowTitle("🚀 TwinStar Quantum에 오신 것을 환영합니다!")
        self.setFixedSize(600, 500)
        self.setStyleSheet("""
            QDialog { background: #131722; }
            QLabel { color: white; }
            QPushButton {
                background: #2962FF;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background: #1e88e5; }
            QPushButton#skip {
                background: transparent;
                color: #787b86;
            }
            QPushButton#skip:hover { color: white; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        # 스텝 인디케이터
        self.indicator_layout = QHBoxLayout()
        self.indicator_layout.setAlignment(Qt.AlignCenter)
        self.indicators = []
        
        for i in range(5):
            dot = QFrame()
            dot.setFixedSize(10, 10)
            dot.setStyleSheet("background: #2a2e3b; border-radius: 5px;")
            self.indicators.append(dot)
            self.indicator_layout.addWidget(dot)
        
        layout.addLayout(self.indicator_layout)
        
        # 컨텐츠 스택
        self.stack = QStackedWidget()
        
        # 단계별 페이지
        steps = [
            self._create_welcome_page(),
            self._create_license_page(),
            self._create_exchange_page(),
            self._create_api_page(),
            self._create_start_page(),
        ]
        
        for step in steps:
            self.stack.addWidget(step)
        
        layout.addWidget(self.stack)
        
        # 버튼
        btn_layout = QHBoxLayout()
        
        self.skip_btn = QPushButton("건너뛰기")
        self.skip_btn.setObjectName("skip")
        self.skip_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.skip_btn)
        
        btn_layout.addStretch()
        
        self.prev_btn = QPushButton("← 이전")
        self.prev_btn.clicked.connect(self._prev_step)
        self.prev_btn.hide()
        btn_layout.addWidget(self.prev_btn)
        
        self.next_btn = QPushButton("다음 →")
        self.next_btn.clicked.connect(self._next_step)
        btn_layout.addWidget(self.next_btn)
        
        layout.addLayout(btn_layout)
        
        self._update_indicators()
    
    def _create_step_page(self, emoji: str, title: str, content: str) -> QWidget:
        """단계 페이지 생성"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignCenter)
        
        # 이모지
        emoji_label = QLabel(emoji)
        emoji_label.setStyleSheet("font-size: 64px;")
        emoji_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(emoji_label)
        
        # 타이틀
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 24px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 내용
        content_label = QLabel(content)
        content_label.setStyleSheet("font-size: 14px; color: #d1d4dc; line-height: 1.6;")
        content_label.setAlignment(Qt.AlignCenter)
        content_label.setWordWrap(True)
        layout.addWidget(content_label)
        
        return page
    
    def _create_welcome_page(self) -> QWidget:
        return self._create_step_page(
            "🚀",
            "TwinStar Quantum",
            "AI 기반 자동 매매 시스템에 오신 것을 환영합니다!\n\n"
            "• 고성능 트렌드 포착 전략\n"
            "• W/M 패턴 실시간 자동 감지\n"
            "• 스마트 손절 및 익절 관리\n\n"
            "다음 단계를 통해 설정을 완료하세요."
        )
    
    def _create_license_page(self) -> QWidget:
        return self._create_step_page(
            "💳",
            "라이선스 활성화",
            "프로그램 사용을 위해 라이선스 활성화가 필요합니다.\n\n"
            "💰 라이선스 문의: 관리자에게 문의하세요\n"
            "💎 지원 결제: USDT (TRC-20)\n\n"
            "결제 후 '수동 활성화' 버튼을 클릭하시면\n"
            "관리자 확인 후 활성화됩니다."
        )
    
    def _create_exchange_page(self) -> QWidget:
        return self._create_step_page(
            "🏦",
            "거래소 선택",
            "지원 거래소를 선택하세요.\n\n"
            "📈 선물 거래:\n"
            "• Bybit (신규 가입 시 수수료 20% 할인)\n"
            "• Binance\n\n"
            "🇰🇷 현물 거래 (한국):\n"
            "• 업비트\n"
            "• 빗썸"
        )
    
    def _create_api_page(self) -> QWidget:
        return self._create_step_page(
            "🔑",
            "API 키 발급",
            "거래소에서 API 키를 발급받으세요.\n\n"
            "1. 거래소 로그인\n"
            "2. API 관리 페이지 이동\n"
            "3. 새 API 키 생성\n"
            "4. 권한 설정 (거래 권한 ON)\n"
            "5. API Key와 Secret Key 복사\n\n"
            "⚠️ 업비트는 IP 화이트리스트 등록 필수!"
        )
    
    def _create_start_page(self) -> QWidget:
        return self._create_step_page(
            "🎯",
            "준비 완료!",
            "이제 자동 매매를 시작할 준비가 되었습니다.\n\n"
            "1. [설정] 탭에서 거래소 연결\n"
            "2. [대시보드] → [매매 시작] 클릭\n"
            "3. 봇이 자동으로 패턴 감지 및 매매\n\n"
            "💡 팁: 처음에는 소액으로 테스트하세요!"
        )
    
    def _next_step(self):
        if self.current_step < 4:
            self.current_step += 1
            self.stack.setCurrentIndex(self.current_step)
            self._update_indicators()
            
            if self.current_step > 0:
                self.prev_btn.show()
            if self.current_step == 4:
                self.next_btn.setText("시작하기 ✓")
        else:
            self.close()
    
    def _prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.stack.setCurrentIndex(self.current_step)
            self._update_indicators()
            
            if self.current_step == 0:
                self.prev_btn.hide()
            self.next_btn.setText("다음 →")
    
    def _update_indicators(self):
        for i, dot in enumerate(self.indicators):
            if i == self.current_step:
                dot.setStyleSheet("background: #2962FF; border-radius: 5px;")
            elif i < self.current_step:
                dot.setStyleSheet("background: #26a69a; border-radius: 5px;")
            else:
                dot.setStyleSheet("background: #2a2e3b; border-radius: 5px;")


def show_onboarding_if_first_run():
    """첫 실행 시 온보딩 표시"""
    import json
    flag_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'first_run.json')
    
    if os.path.exists(flag_file):
        with open(flag_file, 'r') as f:
            data = json.load(f)
            if data.get('completed'):
                return False
    
    # 온보딩 표시
    dialog = OnboardingDialog()
    dialog.exec_()
    
    # 완료 표시
    os.makedirs(os.path.dirname(flag_file), exist_ok=True)
    with open(flag_file, 'w') as f:
        json.dump({'completed': True}, f)
    
    return True


# 테스트
if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    dialog = OnboardingDialog()
    dialog.exec_()
