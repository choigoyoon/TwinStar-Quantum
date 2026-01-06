"""
TwinStar Quantum - 프리미엄 트레이딩 대시보드 v2.0
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QLabel, QTextEdit, QPushButton
)
from PyQt5.QtCore import Qt, QTimer

from GUI.styles.theme import Theme
from GUI.components.status_card import StatusCard
from GUI.components.trade_panel import TradePanel

class TradingDashboardV2(QWidget):
    """프리미엄 트레이딩 대시보드"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(Theme.get_stylesheet())
        self._init_ui()
        self._init_timers()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # === 상단: 상태 카드 ===
        status_layout = QHBoxLayout()
        status_layout.setSpacing(12)
        
        self.balance_card = StatusCard("잔고", "$0.00", "💰")
        self.pnl_card = StatusCard("오늘 PnL", "$0.00", "📈")
        self.position_card = StatusCard("포지션", "0개", "📊")
        self.signal_card = StatusCard("신호", "대기", "🔔")
        
        status_layout.addWidget(self.balance_card)
        status_layout.addWidget(self.pnl_card)
        status_layout.addWidget(self.position_card)
        status_layout.addWidget(self.signal_card)
        
        layout.addLayout(status_layout)
        
        # === 중단: 메인 스플리터 ===
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 좌측: 싱글 트레이딩
        single_group = QGroupBox("싱글 트레이딩")
        single_layout = QVBoxLayout(single_group)
        
        self.single_panel = TradePanel("싱글 매매", mode="single")
        self.single_panel.start_signal.connect(self._on_single_start)
        self.single_panel.stop_signal.connect(self._on_single_stop)
        
        single_layout.addWidget(self.single_panel)
        single_layout.addStretch()
        
        # 우측: 멀티 트레이딩
        multi_group = QGroupBox("멀티 트레이딩")
        multi_layout = QVBoxLayout(multi_group)
        
        self.multi_panel = TradePanel("멀티 스캔", mode="multi")
        self.multi_panel.start_signal.connect(self._on_multi_start)
        self.multi_panel.stop_signal.connect(self._on_multi_stop)
        
        # 멀티 현황
        self.multi_status = QLabel("감시: 0개 | 신호: 0개 | 매매: 0개")
        self.multi_status.setStyleSheet("color: #8b949e; padding: 8px;")
        
        multi_layout.addWidget(self.multi_panel)
        multi_layout.addWidget(self.multi_status)
        multi_layout.addStretch()
        
        main_splitter.addWidget(single_group)
        main_splitter.addWidget(multi_group)
        main_splitter.setSizes([500, 500])
        
        layout.addWidget(main_splitter, stretch=1)
        
        # === 하단: 로그 ===
        log_group = QGroupBox("실시간 로그")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        
        log_layout.addWidget(self.log_text)
        
        layout.addWidget(log_group)
    
    def _init_timers(self):
        # 상태 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_status)
        self.update_timer.start(2000)
    
    def _update_status(self):
        """상태 업데이트"""
        # TODO: 실제 데이터 연동
        pass
    
    def _on_single_start(self, config):
        self.add_log(f"🎯 싱글 매매 시작: {config['symbol']}")
    
    def _on_single_stop(self):
        self.add_log("⏹ 싱글 매매 정지")
    
    def _on_multi_start(self, config):
        self.add_log(f"🔍 멀티 스캔 시작: {config['watch_count']}개 감시")
    
    def _on_multi_stop(self):
        self.add_log("⏹ 멀티 스캔 정지")
    
    def add_log(self, message: str):
        """로그 추가"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def set_balance(self, value: float):
        color = "#3fb950" if value > 0 else "#f85149"
        self.balance_card.set_value(f"${value:,.2f}", color)
    
    def set_pnl(self, value: float):
        color = "#3fb950" if value >= 0 else "#f85149"
        sign = "+" if value >= 0 else ""
        self.pnl_card.set_value(f"{sign}${value:,.2f}", color)
