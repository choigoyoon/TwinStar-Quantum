"""상태 표시 카드"""
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class StatusCard(QFrame):
    """수익/손실 등 상태 표시 카드"""
    
    def __init__(self, title: str, value: str = "-", parent=None):
        super().__init__(parent)
        self._init_ui(title, value)
    
    def _init_ui(self, title: str, value: str):
        self.setStyleSheet("""
            QFrame {
                background-color: #2D2D2D;
                border-radius: 8px;
                padding: 16px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 제목
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("""
            color: #B0B0B0;
            font-size: 12px;
        """)
        layout.addWidget(self.title_label)
        
        # 값
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
        """)
        layout.addWidget(self.value_label)
    
    def set_value(self, value: str, color: str = None):
        self.value_label.setText(value)
        if color:
            self.value_label.setStyleSheet(f"""
                font-size: 24px;
                font-weight: bold;
                color: {color};
            """)
    
    def set_positive(self, value: str):
        self.set_value(value, "#4CAF50")
    
    def set_negative(self, value: str):
        self.set_value(value, "#F44336")
    
    def set_neutral(self, value: str):
        self.set_value(value, "#FFFFFF")
