"""접이식 위젯"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QFrame
)
from ui.design_system.tokens import Colors, Spacing, Radius


class CollapsibleSection(QWidget):
    """펼치기/접기 가능한 섹션"""
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        self._init_ui(title)
    
    def _init_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 헤더 버튼
        self.toggle_btn = QPushButton(f"▶ {title}")
        self.toggle_btn.setStyleSheet(f"""
            QPushButton {{
                text-align: left;
                padding: {Spacing.space_3} {Spacing.space_4};
                background-color: {Colors.bg_elevated};
                border: none;
                border-radius: {Radius.radius_sm};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {Colors.bg_overlay};
            }}
        """)
        self.toggle_btn.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_btn)
        
        # 콘텐츠 영역
        self.content = QFrame()
        self.content.setStyleSheet(f"""
            QFrame {{
                background-color: {Colors.bg_surface};
                border-radius: {Radius.radius_sm};
                padding: {Spacing.space_4};
            }}
        """)
        self.content.setVisible(False)
        self.content_layout = QVBoxLayout(self.content)
        layout.addWidget(self.content)
        
        self.title = title
    
    def toggle(self):
        self.is_expanded = not self.is_expanded
        self.content.setVisible(self.is_expanded)
        arrow = "▼" if self.is_expanded else "▶"
        self.toggle_btn.setText(f"{arrow} {self.title}")
    
    def add_widget(self, widget):
        self.content_layout.addWidget(widget)
    
    def expand(self):
        if not self.is_expanded:
            self.toggle()
    
    def collapse(self):
        if self.is_expanded:
            self.toggle()
