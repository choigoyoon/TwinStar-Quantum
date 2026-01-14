"""
TwinStar Quantum - Dashboard Header
===================================

대시보드 상단 헤더 컴포넌트
- HUD 스타일 상태 표시
- 잔고, PnL, 활성봇, 리스크
"""

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal

from .status_cards import BalanceCard, PnLCard, ActiveBotsCard, RiskCard

# 디자인 시스템
from ui.design_system.tokens import Colors


class DashboardHeader(QWidget):
    """
    대시보드 HUD (Heads-Up Display) 헤더
    
    4개의 상태 카드를 가로로 배치
    
    Signals:
        refresh_clicked: 새로고침 버튼 클릭
    """
    
    refresh_clicked = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 상태 카드들
        self.balance_card = BalanceCard("Wallet Balance")
        self.pnl_card = PnLCard("Daily PnL")
        self.active_card = ActiveBotsCard("Active Bots")
        self.risk_card = RiskCard("Risk Level")
        
        # 높이 고정
        for card in [self.balance_card, self.pnl_card, self.active_card, self.risk_card]:
            card.setFixedHeight(80)
        
        layout.addWidget(self.balance_card)
        layout.addWidget(self.pnl_card)
        layout.addWidget(self.active_card)
        layout.addWidget(self.risk_card)
        
        # 새로고침 버튼
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setFixedSize(36, 36)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {Colors.bg_surface};
                border: 1px solid {Colors.accent_primary};
                border-radius: 18px;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background: {Colors.accent_primary};
            }}
        """)
        self.refresh_btn.clicked.connect(self.refresh_clicked.emit)
        layout.addWidget(self.refresh_btn)
    
    def set_balance(self, value: float, currency: str = "$"):
        """잔고 설정"""
        self.balance_card.set_balance(value, currency)
    
    def set_pnl(self, value: float, currency: str = "$"):
        """PnL 설정"""
        self.pnl_card.set_pnl(value, currency)
    
    def set_active_bots(self, count: int, suffix: str = ""):
        """활성 봇 수 설정"""
        self.active_card.set_count(count, suffix)
    
    def set_risk_level(self, level: str):
        """리스크 레벨 설정"""
        self.risk_card.set_risk_level(level)
    
    def update_all(
        self, 
        balance: float = 0.0,
        pnl: float = 0.0,
        active_bots: int = 0,
        risk_level: str = "safe",
        currency: str = "$"
    ):
        """모든 값 한번에 업데이트"""
        self.set_balance(balance, currency)
        self.set_pnl(pnl, currency)
        self.set_active_bots(active_bots)
        self.set_risk_level(risk_level)
