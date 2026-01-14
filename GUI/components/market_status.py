from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel

class RiskHeaderWidget(QFrame):
    """글로벌 리스크 현황 헤더"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            RiskHeaderWidget {
                background-color: #1e222d;
                border-bottom: 2px solid #2962ff;
                border-radius: 5px;
            }
            QLabel { color: white; font-weight: bold; font-size: 14px; padding: 5px; }
        """)
        self._init_ui()
        
    def _init_ui(self):
        self.setFixedHeight(50)  # [NEW] 높이 고정
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # 1. Total Margin
        self.margin_label = QLabel("Margin Usage: 0.0% (Safe)")
        self.margin_label.setStyleSheet("color: #4CAF50;") # Green default
        layout.addWidget(self.margin_label)
        
        # Separator
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.VLine)
        line1.setStyleSheet("color: #555;")
        layout.addWidget(line1)
        
        # 2. Today PnL
        self.pnl_label = QLabel("Today PnL: $0.00 (0.00%)")
        layout.addWidget(self.pnl_label)

        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.VLine)
        line2.setStyleSheet("color: #555;")
        layout.addWidget(line2)

        # 3. Loss Limit
        self.limit_label = QLabel("Limit: -5.0%")
        self.limit_label.setStyleSheet("color: #FF5252;")
        layout.addWidget(self.limit_label)
        
        # Separator
        line3 = QFrame()
        line3.setFrameShape(QFrame.Shape.VLine)
        line3.setStyleSheet("color: #555;")
        layout.addWidget(line3)

        # 4. MDD & Streak
        self.risk_stat_label = QLabel("MDD: 0.0% | Streak: 0")
        self.risk_stat_label.setStyleSheet("color: #a0a0a0;")
        layout.addWidget(self.risk_stat_label)
        
        layout.addStretch()
        
    def update_status(self, margin_pct, pnl_usd, pnl_pct, mdd=0.0, streak=0):
        # Margin
        margin_color = "#4CAF50" # Safe
        status_text = "(Safe)"
        if margin_pct >= 80:
            margin_color = "#FF5252" # Danger
            status_text = "(Danger!)"
        elif margin_pct >= 50:
            margin_color = "#FFC107" # Warning
            status_text = "(Warning)"
            
        self.margin_label.setText(f"Margin Usage: {margin_pct:.1f}% {status_text}")
        self.margin_label.setStyleSheet(f"color: {margin_color};")
        
        # PnL
        pnl_color = "white"
        if pnl_usd > 0: pnl_color = "#4CAF50"
        elif pnl_usd < 0: pnl_color = "#FF5252"
        
        self.pnl_label.setText(f"Today PnL: ${pnl_usd:.2f} ({pnl_pct:.2f}%)")
        self.pnl_label.setStyleSheet(f"color: {pnl_color};")
        
        # MDD & Streak
        self.risk_stat_label.setText(f"MDD: {mdd:.1f}% | Streak: {streak}")
