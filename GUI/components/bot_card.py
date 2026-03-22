"""실행 중인 봇 정보를 표시하는 프리미엄 카드 컴포넌트"""

from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QGraphicsDropShadowEffect, QProgressBar
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.design_system.tokens import Colors, Radius, Spacing, Typography

class BotCard(QFrame):
    """
    개별 봇 관리 카드
    - 실시간 PnL 표시
    - 심볼 및 거래소 정보
    - 즉시 청산 및 제어 버튼
    """
    
    stop_signal = pyqtSignal(str) # bot_key 전달
    
    def __init__(self, bot_key: str, config: Dict[str, Any]):
        super().__init__()
        self.bot_key = bot_key
        self.config = config
        self.setObjectName("botCard")
        self._init_ui()
        self._apply_style()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            Spacing.i_space_4,  # 16px
            Spacing.i_space_4,
            Spacing.i_space_4,
            Spacing.i_space_4
        )
        layout.setSpacing(Spacing.i_space_3)  # 12px
        
        # 1. Header: Symbol & Exchange
        header = QHBoxLayout()
        
        symbol = self.config.get('symbol', 'Unknown')
        exchange = self.config.get('exchange', 'Unknown').upper()
        
        self.symbol_label = QLabel(symbol)
        self.symbol_label.setStyleSheet(f"font-size: {Typography.text_lg}; font-weight: 700; color: {Colors.text_primary};")
        
        self.exchange_badge = QLabel(exchange)
        self.exchange_badge.setStyleSheet(f"""
            background-color: {Colors.bg_overlay};
            color: {Colors.accent_secondary};
            padding: {Spacing.space_0} {Spacing.space_2};
            border-radius: {Radius.radius_sm};
            font-size: {Typography.text_xs};
            font-weight: 600;
        """)
        
        header.addWidget(self.symbol_label)
        header.addWidget(self.exchange_badge)
        header.addStretch()
        
        # 상태 표시 (Running)
        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet(f"color: {Colors.success}; font-size: {Typography.text_base};")
        header.addWidget(self.status_dot)
        
        layout.addLayout(header)
        
        # 2. Body: PnL & Details
        body = QHBoxLayout()
        
        pnl_layout = QVBoxLayout()
        self.pnl_label = QLabel("$0.00")
        self.pnl_label.setStyleSheet(f"font-size: {Typography.text_2xl}; font-weight: 800; color: {Colors.text_primary};")
        
        self.pnl_pct_label = QLabel("+0.00%")
        self.pnl_pct_label.setStyleSheet(f"font-size: {Typography.text_sm}; font-weight: 600; color: {Colors.text_secondary};")
        
        pnl_layout.addWidget(self.pnl_label)
        pnl_layout.addWidget(self.pnl_pct_label)
        
        body.addLayout(pnl_layout)
        body.addStretch()
        
        # 세부 정보 (레버리지, 방향 등)
        details_layout = QVBoxLayout()
        details_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        lev = self.config.get('leverage', 1)
        self.lev_label = QLabel(f"{lev}x Leverage")
        self.lev_label.setStyleSheet(f"color: {Colors.text_muted}; font-size: {Typography.text_xs};")
        
        side = self.config.get('side', 'Both')
        self.side_label = QLabel(side)
        self.side_label.setStyleSheet(f"color: {Colors.accent_primary}; font-size: {Typography.text_xs}; font-weight: 600;")
        
        details_layout.addWidget(self.lev_label)
        details_layout.addWidget(self.side_label)
        
        body.addLayout(details_layout)
        layout.addLayout(body)
        
        # 3. Progress / Activity Indicator (Sparkline Placeholder)
        self.activity_bar = QProgressBar()
        self.activity_bar.setFixedHeight(2)
        self.activity_bar.setTextVisible(False)
        self.activity_bar.setStyleSheet(f"""
            QProgressBar {{ background-color: {Colors.bg_overlay}; border: none; border-radius: 1px; }}
            QProgressBar::chunk {{ background-color: {Colors.accent_primary}; }}
        """)
        self.activity_bar.setRange(0, 0) # Infinite loading effect for activity
        layout.addWidget(self.activity_bar)
        
        # 4. Footer: Control Buttons
        footer = QHBoxLayout()
        
        self.stop_btn = QPushButton("중단 / 청산")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.danger_bg};
                color: {Colors.danger};
                border: 1px solid {Colors.danger};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_1} {Spacing.space_3};
                font-weight: 600;
                font-size: {Typography.text_sm};
            }}
            QPushButton:hover {{
                background-color: {Colors.danger};
                color: white;
            }}
        """)
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        
        footer.addStretch()
        footer.addWidget(self.stop_btn)
        
        layout.addLayout(footer)

    def _apply_style(self):
        """글래스모피즘 카드 스타일"""
        self.setStyleSheet(f"""
            QFrame#botCard {{
                background-color: {Colors.bg_base};
                border: 1px solid {Colors.border_muted};
                border-radius: {Radius.radius_lg};
            }}
            QFrame#botCard:hover {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.accent_secondary};
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)  # Shadow.shadow_xl 블러 반경과 유사 (24)
        shadow.setColor(Qt.GlobalColor.black)
        shadow.setOffset(0, 5)
        self.setGraphicsEffect(shadow)

    def update_pnl(self, pnl: float, pnl_pct: float):
        """성과 업데이트"""
        color = Colors.success if pnl >= 0 else Colors.danger
        sign = "+" if pnl >= 0 else ""
        
        self.pnl_label.setText(f"{sign}${abs(pnl):,.2f}")
        self.pnl_label.setStyleSheet(f"font-size: {Typography.text_2xl}; font-weight: 800; color: {color};")
        
        self.pnl_pct_label.setText(f"{pnl_pct:+,.2f}%")
        self.pnl_pct_label.setStyleSheet(f"font-size: {Typography.text_sm}; font-weight: 600; color: {color};")
        
        # 호버 효과 색상 업데이트 (동적)
        self.status_dot.setStyleSheet(f"color: {color}; font-size: {Typography.text_base};")

    def _on_stop_clicked(self):
        self.stop_signal.emit(self.bot_key)
