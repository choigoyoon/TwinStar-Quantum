# tier_popup.py - 등급 안내 팝업
"""
TwinStar Quantum 등급 세부 정보 팝업
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QPushButton, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

# 다국어 지원
try:
    from locales import t
except ImportError:
    def t(key, default=None):
        return default if default else key.split('.')[-1]


class TierPopup(QDialog):
    """등급 안내 팝업"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t('tier.title', '💎 등급 안내'))
        self.setFixedSize(600, 450)
        self.setStyleSheet("""
            QDialog {
                background: #1a1a2e;
                color: white;
            }
            QLabel {
                color: white;
            }
            QTableWidget {
                background: #0d1117;
                color: white;
                border: 1px solid #2a2e3b;
                gridline-color: #2a2e3b;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background: #2962ff;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
            QPushButton {
                background: #2962ff;
                color: white;
                border: none;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #1e88e5;
            }
        """)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 제목
        title = QLabel("💎 TwinStar Quantum 등급 안내")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 설명
        desc = QLabel("각 등급별 기능과 가격을 확인하세요")
        desc.setStyleSheet("color: #888; font-size: 12px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)
        
        # 등급 테이블
        table = QTableWidget(5, 5)
        table.setHorizontalHeaderLabels([
            t('tier.name', '등급'),
            t('tier.price', '가격'),
            t('tier.exchanges', '거래소'),
            t('tier.symbols', '심볼'),
            t('tier.features', '주요 기능')
        ])
        
        # 등급 데이터
        tiers = [
            ("🆓 Free", "$0", "0", "1", "백테스트만"),
            ("🔵 Basic", "$29/월", "1개", "3개", "실매매, 텔레그램"),
            ("🟢 Standard", "$59/월", "3개", "10개", "+ 최적화"),
            ("🟡 Premium", "$99/월", "전체", "무제한", "+ 우선 지원"),
            ("🔴 Admin", "-", "전체", "무제한", "관리자 전용"),
        ]
        
        # 등급별 색상
        tier_colors = {
            0: "#888888",  # Free
            1: "#4fc3f7",  # Basic
            2: "#66bb6a",  # Standard
            3: "#ffd54f",  # Premium
            4: "#ff5722",  # Admin
        }
        
        for row, (tier, price, exchanges, symbols, features) in enumerate(tiers):
            items = [tier, price, exchanges, symbols, features]
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 0:
                    item.setForeground(Qt.GlobalColor.white)
                table.setItem(row, col, item)
        
        # 테이블 설정
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setRowHeight(0, 40)
        for i in range(5):
            table.setRowHeight(i, 40)
        
        layout.addWidget(table)
        
        # 하단 안내
        note = QLabel("💡 업그레이드는 설정 탭에서 가능합니다")
        note.setStyleSheet("color: #7c4dff; font-size: 11px;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)
        
        # 닫기 버튼
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        close_btn = QPushButton(t('common.close', '닫기'))
        close_btn.setFixedWidth(120)
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    popup = TierPopup()
    popup.exec()
