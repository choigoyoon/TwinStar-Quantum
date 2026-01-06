"""
TwinStar Quantum - Trading Tab Widget
Organizes Trading Dashboard and Auto Pipeline into sub-tabs.
"""

import logging
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from locales.lang_manager import t

logger = logging.getLogger(__name__)

class TradingTabWidget(QWidget):
    """
    통합 트레이딩 탭
    - 서브탭 1: 실시간 대시보드 (싱글/멀티 매매)
    - 서브탭 2: 자동매매 파이프라인
    """
    def __init__(self, dashboard, auto_pipeline, parent=None):
        super().__init__(parent)
        self.dashboard = dashboard
        self.auto_pipeline = auto_pipeline
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { 
                background: #2b2b2b; 
                color: #888; 
                padding: 10px 20px; 
                font-weight: bold;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected { 
                background: #3c3c3c; 
                color: #00d4aa; 
                border-bottom: 2px solid #00d4aa; 
            }
            QTabBar::tab:hover { background: #333; }
        """)

        # 서브탭 추가
        if self.dashboard:
            self.tabs.addTab(self.dashboard, t("dashboard.manual_trading", "📉 매칭 매매 (싱글/멀티)"))
        
        if self.auto_pipeline:
            self.tabs.addTab(self.auto_pipeline, t("dashboard.auto_pipeline", "⚙️ 자동매매 파이프라인"))

        layout.addWidget(self.tabs)

    def get_dashboard(self):
        return self.dashboard

    def get_auto_pipeline(self):
        return self.auto_pipeline
