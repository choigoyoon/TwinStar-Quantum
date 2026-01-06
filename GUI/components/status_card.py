"""프리미엄 상태 카드 컴포넌트"""

from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt

class StatusCard(QFrame):
    """상태 표시 카드"""
    
    def __init__(self, title: str, value: str = "-", icon: str = ""):
        super().__init__()
        self.setObjectName("statusCard")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # 타이틀
        title_label = QLabel(f"{icon} {title}" if icon else title)
        title_label.setObjectName("titleLabel")
        
        # 값
        self.value_label = QLabel(value)
        self.value_label.setObjectName("valueLabel")
        
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)
    
    def set_value(self, value: str, color: str = None):
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"""
                font-size: 24px;
                font-weight: 700;
                color: {color};
            """)
