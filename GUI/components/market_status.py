from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy
from ui.design_system.tokens import Colors, Radius, Spacing

class RiskHeaderWidget(QFrame):
    """글로벌 리스크 현황 헤더"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            RiskHeaderWidget {{
                background-color: {Colors.bg_surface};
                border-bottom: 2px solid {Colors.accent_primary};
                border-radius: {Radius.radius_md};
            }}
            QLabel {{ color: {Colors.text_primary}; font-weight: bold; font-size: 14px; padding: {Spacing.space_2}; }}
        """)
        self._init_ui()
        
    def _init_ui(self):
        # 반응형 레이아웃
        self.setMinimumHeight(40)
        self.setMaximumHeight(60)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        layout = QHBoxLayout(self)
        spacing = int(Spacing.space_3.replace('px', ''))
        layout.setContentsMargins(spacing, spacing // 2, spacing, spacing // 2)
        
        # 1. Total Margin
        self.margin_label = QLabel("Margin Usage: 0.0% (Safe)")
        self.margin_label.setStyleSheet(f"color: {Colors.success};") # Green default
        layout.addWidget(self.margin_label)
        
        # Separator
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.VLine)
        line1.setStyleSheet(f"color: {Colors.border_default};")
        layout.addWidget(line1)
        
        # 2. Today PnL
        self.pnl_label = QLabel("Today PnL: $0.00 (0.00%)")
        layout.addWidget(self.pnl_label)

        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.VLine)
        line2.setStyleSheet(f"color: {Colors.border_default};")
        layout.addWidget(line2)

        # 3. Loss Limit
        self.limit_label = QLabel("Limit: -5.0%")
        self.limit_label.setStyleSheet(f"color: {Colors.danger};")
        layout.addWidget(self.limit_label)

        # Separator
        line3 = QFrame()
        line3.setFrameShape(QFrame.Shape.VLine)
        line3.setStyleSheet(f"color: {Colors.border_default};")
        layout.addWidget(line3)

        # 4. MDD & Streak
        self.risk_stat_label = QLabel("MDD: 0.0% | Streak: 0")
        self.risk_stat_label.setStyleSheet(f"color: {Colors.text_secondary};")
        layout.addWidget(self.risk_stat_label)
        
        layout.addStretch()
        
    def update_status(self, margin_pct, pnl_usd, pnl_pct, mdd=0.0, streak=0):
        # Margin (동적 색상)
        margin_color = Colors.success # Safe
        status_text = "(Safe)"
        if margin_pct >= 80:
            margin_color = Colors.danger # Danger
            status_text = "(Danger!)"
        elif margin_pct >= 50:
            margin_color = Colors.warning # Warning
            status_text = "(Warning)"

        self.margin_label.setText(f"Margin Usage: {margin_pct:.1f}% {status_text}")
        self.margin_label.setStyleSheet(f"color: {margin_color};")

        # PnL (동적 색상)
        pnl_color = Colors.text_primary
        if pnl_usd > 0:
            pnl_color = Colors.success
        elif pnl_usd < 0:
            pnl_color = Colors.danger

        self.pnl_label.setText(f"Today PnL: ${pnl_usd:.2f} ({pnl_pct:.2f}%)")
        self.pnl_label.setStyleSheet(f"color: {pnl_color};")

        # MDD & Streak
        self.risk_stat_label.setText(f"MDD: {mdd:.1f}% | Streak: {streak}")
