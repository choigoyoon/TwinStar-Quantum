"""
TwinStar Quantum - Base Dialog
==============================

모든 다이얼로그의 기본 클래스
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt

# 디자인 시스템
try:
    from ui.design_system import Colors, Typography, Spacing, Radius
    from ui.design_system.styles import ButtonStyles
except ImportError:
    class Colors:
        bg_surface = "#161b22"
        bg_base = "#0d1117"
        border_default = "#30363d"
        text_primary = "#f0f6fc"
        text_secondary = "#8b949e"
        accent_primary = "#00d4aa"
    class Typography:
        text_xl = "18px"
        text_base = "14px"
        font_semibold = 600
    class Spacing:
        space_4 = "16px"
        space_6 = "24px"
    class Radius:
        radius_lg = "12px"
    ButtonStyles = None


class BaseDialog(QDialog):
    """
    기본 다이얼로그 클래스
    
    새 디자인 시스템이 적용된 다이얼로그 베이스
    
    사용법:
        class MyDialog(BaseDialog):
            def __init__(self):
                super().__init__("제목", "설명")
                self._build_content()
    """
    
    def __init__(
        self, 
        title: str = "",
        description: str = "",
        width: int = 400,
        parent=None
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(width)
        self.setModal(True)
        
        self._title = title
        self._description = description
        
        self._apply_style()
        self._init_base_ui()
    
    def _apply_style(self):
        """스타일 적용"""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.bg_surface};
                border: 1px solid {Colors.border_default};
                border-radius: {Radius.radius_lg};
            }}
        """)
    
    def _init_base_ui(self):
        """기본 UI 구조 생성"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        self.main_layout.setSpacing(16)
        
        # 제목
        if self._title:
            self.title_label = QLabel(self._title)
            self.title_label.setObjectName("dialog-title")
            self.title_label.setStyleSheet(f"""
                font-size: {Typography.text_xl};
                font-weight: {Typography.font_semibold};
                color: {Colors.text_primary};
            """)
            self.main_layout.addWidget(self.title_label)
        
        # 설명
        if self._description:
            self.desc_label = QLabel(self._description)
            self.desc_label.setObjectName("dialog-description")
            self.desc_label.setWordWrap(True)
            self.desc_label.setStyleSheet(f"""
                font-size: {Typography.text_base};
                color: {Colors.text_secondary};
            """)
            self.main_layout.addWidget(self.desc_label)
        
        # 콘텐츠 영역 (서브클래스에서 사용)
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(12)
        self.main_layout.addLayout(self.content_layout)
        
        # 버튼 영역
        self.button_layout = QHBoxLayout()
        self.button_layout.setSpacing(8)
        self.main_layout.addLayout(self.button_layout)
    
    def add_button(
        self, 
        text: str, 
        callback=None, 
        variant: str = "secondary",
        close_on_click: bool = True
    ) -> QPushButton:
        """
        버튼 추가
        
        Args:
            text: 버튼 텍스트
            callback: 클릭 콜백
            variant: 'primary', 'secondary', 'danger'
            close_on_click: 클릭 시 다이얼로그 닫기
        """
        btn = QPushButton(text)
        
        # 스타일 적용
        if variant == "primary":
            style = f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                        stop:0 {Colors.accent_primary}, stop:1 #00b894);
                    color: {Colors.bg_base};
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: #00e6b8;
                }}
            """
        elif variant == "danger":
            style = f"""
                QPushButton {{
                    background: #f85149;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background: #ff6b6b;
                }}
            """
        else:  # secondary
            style = f"""
                QPushButton {{
                    background: {Colors.bg_base};
                    color: {Colors.text_primary};
                    border: 1px solid {Colors.border_default};
                    border-radius: 6px;
                    padding: 10px 20px;
                }}
                QPushButton:hover {{
                    border-color: {Colors.accent_primary};
                }}
            """
        
        btn.setStyleSheet(style)
        
        # 클릭 핸들러
        def on_click():
            if callback:
                callback()
            if close_on_click:
                self.accept()
        
        btn.clicked.connect(on_click)
        self.button_layout.addWidget(btn)
        
        return btn
    
    def add_stretch(self):
        """버튼 영역에 stretch 추가"""
        self.button_layout.addStretch()
    
    def set_content(self, widget):
        """콘텐츠 위젯 설정"""
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.content_layout.addWidget(widget)
