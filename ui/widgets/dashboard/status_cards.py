"""
TwinStar Quantum - Status Card Components
=========================================

대시보드용 상태 카드 컴포넌트들
"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt

# 디자인 시스템
try:
    from ui.design_system import Colors, Typography, Spacing, Radius
except ImportError:
    class Colors:
        bg_surface = "#161b22"
        border_default = "#30363d"
        text_secondary = "#8b949e"
        text_primary = "#f0f6fc"
        accent_primary = "#00d4aa"
        success = "#3fb950"
        danger = "#f85149"
    class Typography:
        text_sm = "12px"
        text_2xl = "24px"
        font_bold = 700
        font_medium = 500
    class Spacing:
        space_3 = "12px"
        space_4 = "16px"
    class Radius:
        radius_lg = "12px"


class StatusCard(QFrame):
    """
    상태 카드 컴포넌트
    
    아이콘 + 라벨 + 값을 표시하는 카드
    
    사용법:
        card = StatusCard("Wallet Balance", "$1,234.56", "💰")
        card.set_value("$2,000.00")
    """
    
    def __init__(
        self, 
        title: str, 
        value: str = "0", 
        icon: str = "",
        accent_color: str = None,
        parent=None
    ):
        super().__init__(parent)
        self.accent_color = accent_color or Colors.accent_primary
        self._init_ui(title, value, icon)
    
    def _init_ui(self, title: str, value: str, icon: str):
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_lg};
            }}
            QFrame:hover {{
                border-color: {self.accent_color};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # 상단: 아이콘 + 제목
        header = QHBoxLayout()
        header.setSpacing(8)
        
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet(f"font-size: 16px;")
            header.addWidget(icon_label)
        
        self.title_label = QLabel(title)
        self.title_label.setObjectName("title")
        self.title_label.setStyleSheet(f"""
            color: {Colors.text_secondary};
            font-size: {Typography.text_sm};
            font-weight: {Typography.font_medium};
        """)
        header.addWidget(self.title_label)
        header.addStretch()
        
        layout.addLayout(header)
        
        # 값
        self.value_label = QLabel(value)
        self.value_label.setObjectName("value")
        self.value_label.setStyleSheet(f"""
            color: {Colors.text_primary};
            font-size: {Typography.text_2xl};
            font-weight: {Typography.font_bold};
        """)
        layout.addWidget(self.value_label)
    
    def set_value(self, value: str):
        """값 업데이트"""
        self.value_label.setText(value)
    
    def set_title(self, title: str):
        """제목 업데이트"""
        self.title_label.setText(title)
    
    def set_accent(self, color: str):
        """강조 색상 변경"""
        self.accent_color = color
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_lg};
            }}
            QFrame:hover {{
                border-color: {color};
            }}
        """)


class PnLCard(StatusCard):
    """
    PnL (손익) 전용 카드
    
    값에 따라 자동으로 색상 변경 (수익: 초록, 손실: 빨강)
    """
    
    def __init__(self, title: str = "Daily PnL", parent=None):
        super().__init__(title, "$0.00", "📈", parent=parent)
        self._pnl_value = 0.0
    
    def set_pnl(self, value: float, currency: str = "$"):
        """PnL 값 설정 (색상 자동 변경)"""
        self._pnl_value = value
        
        # 색상 결정
        if value >= 0:
            color = Colors.success
            prefix = "+"
        else:
            color = Colors.danger
            prefix = ""
        
        # 값 포맷
        formatted = f"{prefix}{currency}{abs(value):,.2f}"
        self.value_label.setText(formatted)
        self.value_label.setStyleSheet(f"""
            color: {color};
            font-size: {Typography.text_2xl};
            font-weight: {Typography.font_bold};
        """)
    
    @property
    def pnl_value(self) -> float:
        return self._pnl_value


class BalanceCard(StatusCard):
    """
    잔고 전용 카드
    
    통화 포맷팅 지원
    """
    
    def __init__(self, title: str = "Wallet Balance", parent=None):
        super().__init__(title, "$0.00", "💰", Colors.success, parent)
        self._balance = 0.0
    
    def set_balance(self, value: float, currency: str = "$"):
        """잔고 설정"""
        self._balance = value
        formatted = f"{currency}{value:,.2f}"
        self.value_label.setText(formatted)
    
    @property
    def balance(self) -> float:
        return self._balance


class RiskCard(StatusCard):
    """
    리스크 레벨 카드
    
    리스크 레벨에 따라 색상 자동 변경
    """
    
    RISK_COLORS = {
        "safe": Colors.success,
        "low": "#7cb342",
        "medium": "#ffb300",
        "high": "#ff7043",
        "critical": Colors.danger,
    }
    
    def __init__(self, title: str = "Risk Level", parent=None):
        super().__init__(title, "Safe", "🛡️", parent=parent)
        self._risk_level = "safe"
    
    def set_risk_level(self, level: str):
        """리스크 레벨 설정"""
        level = level.lower()
        self._risk_level = level
        
        color = self.RISK_COLORS.get(level, Colors.text_secondary)
        display = level.capitalize()
        
        self.value_label.setText(display)
        self.value_label.setStyleSheet(f"""
            color: {color};
            font-size: {Typography.text_2xl};
            font-weight: {Typography.font_bold};
        """)
        self.set_accent(color)
    
    @property
    def risk_level(self) -> str:
        return self._risk_level


class ActiveBotsCard(StatusCard):
    """
    활성 봇 카드
    """
    
    def __init__(self, title: str = "Active Bots", parent=None):
        super().__init__(title, "0", "🤖", Colors.accent_primary, parent)
        self._count = 0
    
    def set_count(self, count: int, suffix: str = ""):
        """활성 봇 수 설정"""
        self._count = count
        
        if suffix:
            text = f"{count} {suffix}"
        else:
            text = str(count)
        
        self.value_label.setText(text)
        
        # 0이면 회색, 아니면 민트색
        if count == 0:
            color = Colors.text_secondary
        else:
            color = Colors.accent_primary
        
        self.value_label.setStyleSheet(f"""
            color: {color};
            font-size: {Typography.text_2xl};
            font-weight: {Typography.font_bold};
        """)
    
    @property
    def count(self) -> int:
        return self._count
