"""
TwinStar Quantum - Layout Optimized Dashboard (v4.3)
가독성 및 공간 효율성을 극대화한 2열 탭 레이아웃
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QGroupBox, QLabel, QTextEdit, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer

from GUI.components.status_card import StatusCard
from GUI.components.trade_panel import TradePanel

class TradingDashboardV3(QWidget):
    """공간 최적화형 대시보드 (v4.3)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.confirmed_layout = False
        self._init_ui()
        self._init_timers()
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # === 1. Top HUD (Heads-Up Display) ===
        # 높이를 줄이고 핵심 정보만 표시
        hud_layout = QHBoxLayout()
        hud_layout.setSpacing(12)
        
        self.balance_card = StatusCard("Wallet Balance", "$0.00", "💰")
        self.pnl_card = StatusCard("Daily PnL", "$0.00", "📈")
        self.active_card = StatusCard("Active Bots", "0 Moving", "🤖")
        self.risk_card = StatusCard("Risk Level", "Safe", "🛡️")
        
        # 카드 높이 강제 조절 (Compact)
        for card in [self.balance_card, self.pnl_card, self.active_card, self.risk_card]:
            card.setFixedHeight(80)
            
        hud_layout.addWidget(self.balance_card)
        hud_layout.addWidget(self.pnl_card)
        hud_layout.addWidget(self.active_card)
        hud_layout.addWidget(self.risk_card)
        
        layout.addLayout(hud_layout)
        
        # === 2. Main Workspace (Splitter) ===
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setHandleWidth(2)
        
        # --- Left Panel: Control Center (Tabs) ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.control_tabs = QTabWidget()
        self.control_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; }
            QTabBar::tab { height: 32px; width: 120px; }
        """)
        
        # Tab 1: Single Trading
        self.single_panel = TradePanel("Single Sniper", mode="single")
        self.control_tabs.addTab(self.single_panel, "🎯 Single Trade")
        
        # Tab 2: Multi Trading
        self.multi_panel = TradePanel("Multi Explorer", mode="multi")
        self.control_tabs.addTab(self.multi_panel, "🔍 Multi Scan")
        
        left_layout.addWidget(self.control_tabs)
        
        # --- Right Panel: Monitor & Logs (Vertical Splitter) ---
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.setHandleWidth(2)
        
        # Top Right: Positions & Charts
        monitor_group = QGroupBox("Market Monitor")
        monitor_layout = QVBoxLayout(monitor_group)
        
        # (Placeholder for generic position list)
        self.pos_label = QLabel("No Active Positions")
        self.pos_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pos_label.setStyleSheet("font-size: 14px; color: #5f6368;")
        
        # Real position contents would go here
        monitor_layout.addWidget(self.pos_label)
        monitor_layout.addStretch()
        
        # Bottom Right: Logs
        log_group = QGroupBox("System Logs")
        log_layout = QVBoxLayout(log_group)
        log_layout.setContentsMargins(4, 16, 4, 4)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setPlaceholderText("System initialized based on Alpha-X7 Core...")
        
        log_layout.addWidget(self.log_text)
        
        # Add to Right Splitter
        right_splitter.addWidget(monitor_group)
        right_splitter.addWidget(log_group)
        right_splitter.setSizes([500, 300]) # Position: 500px, Log: 300px
        
        # Add to Main Splitter
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_splitter)
        
        # 비율 6:4 (컨트롤:모니터)
        main_splitter.setStretchFactor(0, 6)
        main_splitter.setStretchFactor(1, 4)
        
        layout.addWidget(main_splitter)
        
    def _init_timers(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._fake_update)
        self.timer.start(1000)
        
    def _fake_update(self):
        # 데모용 업데이트
        pass
        
    def add_log(self, msg):
        from datetime import datetime
        ts = datetime.now().strftime("[%H:%M:%S]")
        self.log_text.append(f"{ts} {msg}")

# Test code
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    w = TradingDashboardV3()
    w.resize(1280, 800)
    w.show()
    sys.exit(app.exec())
